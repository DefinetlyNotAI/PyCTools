#define WIN32_NO_STATUS
#include <windows.h>     // Brings in winnt.h without NTSTATUS definitions
#undef WIN32_NO_STATUS
#include <ntstatus.h>    // Now pulls in the NTSTATUS codes without conflict

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <immintrin.h>   // For _rdrand32_step
#include <intrin.h>      // For __cpuid
#include <mmsystem.h>    // For waveIn functions
#include <iphlpapi.h>    // For network stats
#include <psapi.h>       // For GetProcessMemoryInfo
#include <powrprof.h>    // For battery info

#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "powrprof.lib")

// Define DLL export macro for cleaner syntax
#define HRNG_API __declspec(dllexport)

// Secure mixing function using SHA-256
static int mix_entropy(unsigned char* buffer, unsigned char* new_data, const size_t data_size) {
    BCRYPT_ALG_HANDLE hAlg = NULL;
    BCRYPT_HASH_HANDLE hHash = NULL;
    DWORD hashSize = 0, resultSize = 0;
    NTSTATUS status = STATUS_SUCCESS;
    int success = 0;
    unsigned char* temp_buffer = NULL;

    // Initialize algorithm provider
    status = BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_SHA256_ALGORITHM, NULL, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    // Get hash object size
    status = BCryptGetProperty(hAlg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&hashSize,
                               sizeof(hashSize), &resultSize, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    // Allocate memory for hash object
    temp_buffer = (unsigned char*)HeapAlloc(GetProcessHeap(), 0, hashSize);
    if (!temp_buffer) goto cleanup;

    // Create hash object
    status = BCryptCreateHash(hAlg, &hHash, temp_buffer, hashSize, NULL, 0, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    // Hash existing buffer
    status = BCryptHashData(hHash, buffer, 32, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    // Hash new data
    status = BCryptHashData(hHash, new_data, (ULONG)data_size, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    // Finalize hash
    status = BCryptFinishHash(hHash, buffer, 32, 0);
    if (!BCRYPT_SUCCESS(status)) goto cleanup;

    success = 1;

cleanup:
    if (hHash) BCryptDestroyHash(hHash);
    if (hAlg) BCryptCloseAlgorithmProvider(hAlg, 0);
    if (temp_buffer) HeapFree(GetProcessHeap(), 0, temp_buffer);

    return success;
}

// Safely execute CPUID instruction (no SEH, just call)
static int safe_cpuid(int cpuInfo[4], const int function_id) {
    __cpuid(cpuInfo, function_id);
    return 1;
}

// Check if CPU supports RDRAND instruction
HRNG_API int has_rdrand() {
    int info[4] = {0};
    safe_cpuid(info, 1);
    // Bit 30 of ECX indicates RDRAND support
    return (info[2] & (1 << 30)) != 0;
}

// Fill buffer with hardware RNG bytes using RDRAND with retry logic
HRNG_API int read_hwrng(unsigned char* buffer, const int size) {
    if (!buffer || size <= 0) {
        return 0; // Invalid parameters
    }

    const int has_rdrand_support = has_rdrand();

    // If RDRAND is not supported, fall back to BCryptGenRandom
    if (!has_rdrand_support) {
        const NTSTATUS status = BCryptGenRandom(NULL, buffer, size,
                                         BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        return BCRYPT_SUCCESS(status) ? 1 : 0;
    }

    // Use a structured exception handling block for RDRAND operations
    int i = 0;
    uint32_t rnd;

    while (i < size) {
        const int MAX_RETRIES = 10;
        int success = 0;

        // Try multiple times if RDRAND fails
        for (int retry = 0; retry < MAX_RETRIES && !success; retry++) {
            success = _rdrand32_step(&rnd);
            if (!success) Sleep(1); // Small delay between retries
        }

        if (!success) {
            // Fall back to BCryptGenRandom if RDRAND keeps failing
            const NTSTATUS status = BCryptGenRandom(NULL, buffer + i, size - i,
                                             BCRYPT_USE_SYSTEM_PREFERRED_RNG);
            return BCRYPT_SUCCESS(status) ? 1 : 0;
        }

        for (int j = 0; j < 4 && i < size; ++j, ++i) {
            buffer[i] = (rnd >> (j * 8)) & 0xFF;
        }
    }

    return 1;
}

// Get system performance info as entropy
static int get_performance_entropy(unsigned char *buffer) {
    if (!buffer) return 0;

    FILETIME idleTime, kernelTime, userTime;
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);

    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime) ||
        !GlobalMemoryStatusEx(&memInfo)) {
        return 0;
    }

    // Mix different timing and memory values
    ULARGE_INTEGER idle, kernel, user, diskRead, diskWrite;
    idle.LowPart = idleTime.dwLowDateTime;
    idle.HighPart = idleTime.dwHighDateTime;
    kernel.LowPart = kernelTime.dwLowDateTime;
    kernel.HighPart = kernelTime.dwHighDateTime;
    user.LowPart = userTime.dwLowDateTime;
    user.HighPart = userTime.dwHighDateTime;

    // Get disk I/O information
    IO_COUNTERS ioCounters;
    if (!GetProcessIoCounters(GetCurrentProcess(), &ioCounters)) {
        return 0;
    }

    diskRead.QuadPart = ioCounters.ReadTransferCount;
    diskWrite.QuadPart = ioCounters.WriteTransferCount;

    // Process memory information
    PROCESS_MEMORY_COUNTERS pmc;
    if (!GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        return 0;
    }

    // Get high-precision timer
    LARGE_INTEGER perfCounter, perfFreq;
    QueryPerformanceCounter(&perfCounter);
    QueryPerformanceFrequency(&perfFreq);

    // Fill the buffer with collected entropy
    memcpy(buffer, &idle.QuadPart, 8);
    memcpy(buffer + 8, &perfCounter.QuadPart, 8);
    memcpy(buffer + 16, &kernel.QuadPart, 8);
    memcpy(buffer + 24, &user.QuadPart, 8);
    memcpy(buffer + 32, &memInfo.ullAvailPhys, 8);
    memcpy(buffer + 40, &memInfo.ullTotalPhys, 8);
    memcpy(buffer + 48, &diskRead.QuadPart, 8);
    memcpy(buffer + 56, &diskWrite.QuadPart, 8);

    // Add process info
    memcpy(buffer + 64, &pmc.WorkingSetSize, 8);
    memcpy(buffer + 72, &pmc.PagefileUsage, 8);

    return 1;
}

// Get audio data from microphone as entropy source
static int get_audio_entropy(unsigned char* buffer) {
    if (!buffer) return 0;

    HWAVEIN hWaveIn = NULL;
    WAVEHDR waveHdr = {0};
    WAVEFORMATEX wfx = {0};
    int success = 0;
    unsigned char* audioBuffer = NULL;

    wfx.wFormatTag = WAVE_FORMAT_PCM;
    wfx.nChannels = 1;
    wfx.nSamplesPerSec = 8000;
    wfx.wBitsPerSample = 8;
    wfx.nBlockAlign = wfx.nChannels * wfx.wBitsPerSample / 8;
    wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign;

    // Try to open any available audio device
    MMRESULT result = waveInOpen(&hWaveIn, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
    if (result != MMSYSERR_NOERROR) {
        // No audio device available - fill with ticks instead
        const DWORD ticks = GetTickCount();
        for (size_t i = 0; i < 128; i++) {
            buffer[i] = (unsigned char)((ticks + i) & 0xFF);
        }
        return 1; // Return success anyway
    }

    // Prepare wave buffer
    audioBuffer = (unsigned char*)HeapAlloc(GetProcessHeap(), 0, 128);
    if (!audioBuffer) {
        waveInClose(hWaveIn);
        return 0;
    }

    waveHdr.lpData = (LPSTR)audioBuffer;
    waveHdr.dwBufferLength = (DWORD)128;

    result = waveInPrepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
    if (result != MMSYSERR_NOERROR) {
        HeapFree(GetProcessHeap(), 0, audioBuffer);
        waveInClose(hWaveIn);
        return 0;
    }

    // Add the buffer to audio input
    result = waveInAddBuffer(hWaveIn, &waveHdr, sizeof(WAVEHDR));
    if (result != MMSYSERR_NOERROR) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
        HeapFree(GetProcessHeap(), 0, audioBuffer);
        waveInClose(hWaveIn);
        return 0;
    }

    // Start recording
    result = waveInStart(hWaveIn);
    if (result != MMSYSERR_NOERROR) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
        HeapFree(GetProcessHeap(), 0, audioBuffer);
        waveInClose(hWaveIn);
        return 0;
    }

    // Wait for buffer to fill (with timeout)
    const DWORD startTime = GetTickCount();
    while (!(waveHdr.dwFlags & WHDR_DONE)) {
        Sleep(10);
        if (GetTickCount() - startTime > 500) break; // 500ms timeout
    }

    // Copy whatever data we got
    memcpy(buffer, audioBuffer, 128);
    success = 1;

    // Cleanup
    waveInStop(hWaveIn);
    waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
    waveInClose(hWaveIn);
    HeapFree(GetProcessHeap(), 0, audioBuffer);

    return success;
}

// Get battery/power information as entropy source
static int get_battery_entropy(unsigned char* buffer) {
    if (!buffer) return 0;

    SYSTEM_POWER_STATUS powerStatus;
    if (!GetSystemPowerStatus(&powerStatus)) {
        return 0;
    }

    // Get detailed battery information if available
    SYSTEM_BATTERY_STATE batteryState;
    if (CallNtPowerInformation(SystemBatteryState, NULL, 0,
                              &batteryState, sizeof(batteryState)) == STATUS_SUCCESS) {
        memcpy(buffer, &batteryState, min(128, sizeof(batteryState)));
    } else {
        // Fall back to basic power information
        memcpy(buffer, &powerStatus, min(128, sizeof(powerStatus)));
    }

    return 1;
}

// Get network statistics as entropy
static int get_network_entropy(unsigned char* buffer) {
    if (!buffer) return 0;

    // Get adapter info
    IP_ADAPTER_INFO adapterInfo[16];
    ULONG bufLen = sizeof(adapterInfo);
    const DWORD result = GetAdaptersInfo(adapterInfo, &bufLen);

    if (result != ERROR_SUCCESS) {
        return 0;
    }

    // Get TCP statistics
    MIB_TCPSTATS tcpStats;
    if (GetTcpStatistics(&tcpStats) != NO_ERROR) {
        return 0;
    }

    // Fill buffer with network data
    memcpy(buffer, &tcpStats, min(128, sizeof(tcpStats)));

    return 1;
}

// Get CPU-specific entropy using RDTSC and other hardware features
static int get_cpu_entropy(unsigned char* buffer) {
    if (!buffer) return 0;

    // Get cycles using RDTSC
    unsigned __int64 cycles;

    cycles = __rdtsc();
    memcpy(buffer, &cycles, sizeof(cycles));

    // CPU information
    int cpuInfo[4] = {0};
    safe_cpuid(cpuInfo, 0);
    memcpy(buffer + 8, cpuInfo, 16);

    return 1;
}

// MaxRNG: Uses multiple entropy sources and mixes them together
HRNG_API int MaxRNG(unsigned char* buffer, const int size) {
    if (!buffer || size <= 0) {
        return 0;
    }

    // Allocate temporary buffers for entropy collection
    unsigned char* temp_buffer = NULL;
    const size_t TEMP_SIZE = 128;  // Minimum size for various entropy sources
    int success = 0;

    // Initialize the output buffer with initial entropy from system RNG
    if (!BCRYPT_SUCCESS(BCryptGenRandom(NULL, buffer, size, BCRYPT_USE_SYSTEM_PREFERRED_RNG))) {
        return 0;
    }

    // Allocate temp buffer for entropy sources
    temp_buffer = (unsigned char*)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, TEMP_SIZE);
    if (!temp_buffer) {
        return 0;
    }

    do {
        // Collect entropy from hardware RNG if available (RDRAND)
        if (has_rdrand()) {
            if (!read_hwrng(temp_buffer, (int)min(TEMP_SIZE, size))) {
                // Fall back to BCryptGenRandom if RDRAND fails
                if (!BCRYPT_SUCCESS(BCryptGenRandom(NULL, temp_buffer, (ULONG)min(TEMP_SIZE, size),
                                                   BCRYPT_USE_SYSTEM_PREFERRED_RNG))) {
                    break;
                }
            }
            // Mix hardware RNG entropy into buffer
            if (!mix_entropy(buffer, temp_buffer, min(TEMP_SIZE, size))) break;
        }

        // Collect and mix CPU entropy
        if (get_cpu_entropy(temp_buffer)) {
            if (!mix_entropy(buffer, temp_buffer, TEMP_SIZE)) break;
        }

        // Collect and mix performance/timing entropy
        if (get_performance_entropy(temp_buffer)) {
            if (!mix_entropy(buffer, temp_buffer, TEMP_SIZE)) break;
        }

        // Collect and mix audio entropy (or timing data if no mic available)
        if (get_audio_entropy(temp_buffer)) {
            if (!mix_entropy(buffer, temp_buffer, TEMP_SIZE)) break;
        }

        // Collect and mix battery/power entropy
        if (get_battery_entropy(temp_buffer)) {
            if (!mix_entropy(buffer, temp_buffer, TEMP_SIZE)) break;
        }

        // Collect and mix network entropy
        if (get_network_entropy(temp_buffer)) {
            if (!mix_entropy(buffer, temp_buffer, TEMP_SIZE)) break;
        }

        // Final mixing with high-precision timer
        LARGE_INTEGER counter;
        QueryPerformanceCounter(&counter);
        memcpy(temp_buffer, &counter, sizeof(counter));
        if (!mix_entropy(buffer, temp_buffer, sizeof(counter))) break;

        success = 1;
    } while (0); // Non-looping do-while to allow for breaks

    // Securely clean up the temporary buffer
    SecureZeroMemory(temp_buffer, TEMP_SIZE);
    HeapFree(GetProcessHeap(), 0, temp_buffer);

    return success;
}

// Additional extended entropy gathering for MaxRNG
HRNG_API int MaxRNG_Extended(unsigned char* buffer, const int size, const int intensive_level) {
    if (!buffer || size <= 0 || intensive_level < 0) {
        return 0;
    }

    unsigned char* temp_buffer = NULL;
    const size_t TEMP_SIZE = 256;  // Larger temp buffer for extended entropy
    int success = 0;
    const int iterations = intensive_level > 0 ? intensive_level : 1;

    // First do a regular MaxRNG call
    if (!MaxRNG(buffer, size)) {
        return 0;
    }

    // For higher security levels, perform multiple iterations of mixing
    if (intensive_level <= 1) {
        return 1; // Standard MaxRNG is enough for basic usage
    }

    // Allocate temp buffer for additional entropy passes
    temp_buffer = (unsigned char*)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, TEMP_SIZE);
    if (!temp_buffer) {
        return 0;
    }

    do {
        // Additional entropy gathering based on intensity level
        for (int i = 0; i < iterations; i++) {
            // Mix in more CPU jitter by performing intensive calculations
            LARGE_INTEGER start, end;
            QueryPerformanceCounter(&start);

            // CPU-intensive operation to generate timing differences
            volatile double result = 1.0;
            for (int j = 0; j < 1000; j++) {
                result *= 1.000001;
            }

            QueryPerformanceCounter(&end);

            // Mix in the timing results
            memcpy(temp_buffer, &start, sizeof(start));
            memcpy(temp_buffer + sizeof(start), &end, sizeof(end));
            memcpy(temp_buffer + sizeof(start) + sizeof(end), (const void *)&result, sizeof(result));
            if (!mix_entropy(buffer, temp_buffer, sizeof(start) + sizeof(end) + sizeof(double))) {
                break;
            }

            // Add a small sleep to allow system state to change
            Sleep(1);

            // For the highest intensity levels, gather more system state
            if (intensive_level >= 3) {
                // Get multiple CPU info samples
                for (int cpuid_leaf = 0; cpuid_leaf < 4; cpuid_leaf++) {
                    int cpu_info[4];
                    safe_cpuid(cpu_info, cpuid_leaf);
                    memcpy(temp_buffer + cpuid_leaf * 16, cpu_info, 16);
                }

                if (!mix_entropy(buffer, temp_buffer, 64)) {
                    break;
                }

                // Gather disk I/O timing entropy
                // ReSharper disable once CppLocalVariableMayBeConst
                HANDLE hFile = CreateFile("NUL", GENERIC_WRITE,
                                          FILE_SHARE_READ | FILE_SHARE_WRITE,
                                          NULL, OPEN_EXISTING, 0, NULL);
                if (hFile != INVALID_HANDLE_VALUE) {
                    const char dummy[16] = {0};
                    DWORD written = 0;

                    QueryPerformanceCounter(&start);
                    WriteFile(hFile, dummy, sizeof(dummy), &written, NULL);
                    QueryPerformanceCounter(&end);

                    CloseHandle(hFile);

                    memcpy(temp_buffer, &start, sizeof(start));
                    memcpy(temp_buffer + sizeof(start), &end, sizeof(end));

                    if (!mix_entropy(buffer, temp_buffer, sizeof(start) + sizeof(end))) {
                        break;
                    }
                }
            }
        }

        success = 1;
    } while (0); // Non-looping do-while to allow for breaks

    SecureZeroMemory(temp_buffer, TEMP_SIZE);
    HeapFree(GetProcessHeap(), 0, temp_buffer);

    return success;
}

// Self-test function to verify RNG functionality
HRNG_API int RNG_SelfTest(void) {
    unsigned char buffer1[32] = {0};
    unsigned char buffer2[32] = {0};
    int success = 0;

    // Test hardware RNG if available
    if (has_rdrand()) {
        if (!read_hwrng(buffer1, sizeof(buffer1))) {
            return 0; // Hardware RNG failed
        }

        // Make sure we're not getting all zeros
        int allZeros = 1;
        for (int i = 0; i < sizeof(buffer1); i++) {
            if (buffer1[i] != 0) {
                allZeros = 0;
                break;
            }
        }

        if (allZeros) return 0; // Hardware RNG returned all zeros

        // Test a second read to ensure different values
        if (!read_hwrng(buffer2, sizeof(buffer2))) {
            return 0; // Second hardware RNG read failed
        }

        // Outputs should be different
        if (memcmp(buffer1, buffer2, sizeof(buffer1)) == 0) {
            return 0; // Hardware RNG returned identical sequences
        }
    }

    // Test MaxRNG
    memset(buffer1, 0, sizeof(buffer1));
    memset(buffer2, 0, sizeof(buffer2));

    if (!MaxRNG(buffer1, sizeof(buffer1))) {
        return 0; // MaxRNG failed
    }

    if (!MaxRNG(buffer2, sizeof(buffer2))) {
        return 0; // Second MaxRNG call failed
    }

    // Outputs should be different
    if (memcmp(buffer1, buffer2, sizeof(buffer1)) == 0) {
        return 0; // MaxRNG returned identical sequences
    }

    success = 1;
    return success;
}

static CRITICAL_SECTION g_initMutex;
static CRITICAL_SECTION g_rngMutex;
static volatile LONG g_rngInitialized = 0; // atomic flag (0 = false, 1 = true)

static void InitializeRNG() {
    // Double-checked locking pattern:
    if (InterlockedCompareExchange(&g_rngInitialized, 1, 1) == 0) {
        // Acquire init mutex to synchronize
        EnterCriticalSection(&g_initMutex);

        if (g_rngInitialized == 0) {
            InitializeCriticalSection(&g_rngMutex);
            g_rngInitialized = 1;
        }

        LeaveCriticalSection(&g_initMutex);
    }
}

HRNG_API int MaxRNG_ThreadSafe(unsigned char* buffer, const int size) {
    if (g_rngInitialized == 0) {
        InitializeRNG();
    }

    EnterCriticalSection(&g_rngMutex);
    int result = MaxRNG(buffer, size);
    LeaveCriticalSection(&g_rngMutex);

    return result;
}

// DLL main entry point
BOOL WINAPI DllMain(const DWORD fdwReason) {
    switch (fdwReason) {
        case DLL_PROCESS_ATTACH:
            // Initialize RNG when DLL is loaded
            InitializeRNG();
            break;
        case DLL_PROCESS_DETACH:
            // Clean up resources if needed
            if (g_rngInitialized) {
                DeleteCriticalSection(&g_rngMutex);
                g_rngInitialized = 0;
            }
            break;
        default:
            break;
    }
    return TRUE;
}
