#define CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <intrin.h>
#include <stdint.h>
#include <bcrypt.h>
#include <psapi.h>
#include <iphlpapi.h>
#include <stdio.h>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")

// Globals for thread safety
static CRITICAL_SECTION g_rngLock;
static volatile LONG g_threadingInitialized = 0;


static int rdrand_supported()
{
    int cpuInfo[4];
    __cpuid(cpuInfo, 1);
    return (cpuInfo[2] & (1 << 30)) != 0;
}

// Retry RDRAND 10 times max
static int rdrand32_retry(uint32_t *val)
{
    for (int i = 0; i < 10; i++)
    {
        if (_rdrand32_step(val))
            return 1;
    }
    return 0;
}

// Collect CPU info entropy: CPUID and RDTSC
static void collect_cpu_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    int cpuInfo[4];
    __cpuid(cpuInfo, 0);
    BCryptHashData(hHash, (PUCHAR)cpuInfo, sizeof(cpuInfo), 0);

    __cpuid(cpuInfo, 1);
    BCryptHashData(hHash, (PUCHAR)cpuInfo, sizeof(cpuInfo), 0);

    uint64_t tsc = __rdtsc();
    BCryptHashData(hHash, (PUCHAR)&tsc, sizeof(tsc), 0);
}

// Process memory info entropy
static void collect_process_memory_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    PROCESS_MEMORY_COUNTERS pmc = { 0 };
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc)))
    {
        BCryptHashData(hHash, (PUCHAR)&pmc, sizeof(pmc), 0);
    }
}

// Performance counter entropy
static void collect_perf_counter_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    LARGE_INTEGER counter;
    if (QueryPerformanceCounter(&counter))
    {
        BCryptHashData(hHash, (PUCHAR)&counter, sizeof(counter), 0);
    }
}

// Disk free space entropy
static void collect_disk_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    ULARGE_INTEGER freeBytesAvailable, totalNumberOfBytes, totalNumberOfFreeBytes;
    if (GetDiskFreeSpaceExA("C:\\", &freeBytesAvailable, &totalNumberOfBytes, &totalNumberOfFreeBytes))
    {
        BCryptHashData(hHash, (PUCHAR)&freeBytesAvailable, sizeof(freeBytesAvailable), 0);
        BCryptHashData(hHash, (PUCHAR)&totalNumberOfBytes, sizeof(totalNumberOfBytes), 0);
        BCryptHashData(hHash, (PUCHAR)&totalNumberOfFreeBytes, sizeof(totalNumberOfFreeBytes), 0);
    }
}

// Audio entropy fallback (simple timing fallback)
static void collect_audio_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    // Simplified: no real audio capture to keep minimal
    // Just hash QueryPerformanceCounter several times with Sleep
    for (int i = 0; i < 5; i++)
    {
        LARGE_INTEGER counter;
        QueryPerformanceCounter(&counter);
        BCryptHashData(hHash, (PUCHAR)&counter, sizeof(counter), 0);
        Sleep(10);
    }
}

// Battery info entropy
static void collect_battery_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    SYSTEM_POWER_STATUS status = { 0 };
    if (GetSystemPowerStatus(&status))
    {
        BCryptHashData(hHash, (PUCHAR)&status, sizeof(status), 0);
    }
}

// Network stats entropy
static void collect_network_entropy(const BCRYPT_HASH_HANDLE hHash)
{
    MIB_TCPSTATS stats = { 0 };
    if (GetTcpStatistics(&stats) == NO_ERROR)
    {
        BCryptHashData(hHash, (PUCHAR)&stats, sizeof(stats), 0);
    }

    // Adapter info
    ULONG size = 0;
    GetAdaptersInfo(NULL, &size);
    if (size > 0)
    {
        // ReSharper disable once CppLocalVariableMayBeConst
        PIP_ADAPTER_INFO pAdapterInfo = (PIP_ADAPTER_INFO)malloc(size);
        if (pAdapterInfo)
        {
            if (GetAdaptersInfo(pAdapterInfo, &size) == NO_ERROR)
            {
                BCryptHashData(hHash, (PUCHAR)pAdapterInfo, size, 0);
            }
            free(pAdapterInfo);
        }
    }
}

// Combine all entropy sources and hash to buffer with complexity rounds
static int collect_entropy(unsigned char *buffer, const int size, const int complexity)
{
    BCRYPT_ALG_HANDLE hAlg = NULL;
    BCRYPT_HASH_HANDLE hHash = NULL;
    DWORD cbHash = 0, cbData = 0;
    unsigned char hash[32]; // SHA256

    NTSTATUS status = BCryptOpenAlgorithmProvider(&hAlg, BCRYPT_SHA256_ALGORITHM, NULL, 0);
    if (!BCRYPT_SUCCESS(status)) return 0;

    status = BCryptGetProperty(hAlg, BCRYPT_HASH_LENGTH, (PUCHAR)&cbHash, sizeof(DWORD), &cbData, 0);
    if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }
    if (cbHash != 32) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    // Create hash object
    status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
    if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    for (int round = 0; round < complexity; round++)
    {
        // RDRAND entropy
        if (rdrand_supported())
        {
            uint32_t rndVal = 0;
            if (rdrand32_retry(&rndVal))
            {
                BCryptHashData(hHash, (PUCHAR)&rndVal, sizeof(rndVal), 0);
            }
        }

        collect_cpu_entropy(hHash);
        collect_process_memory_entropy(hHash);
        collect_perf_counter_entropy(hHash);
        collect_disk_entropy(hHash);
        collect_audio_entropy(hHash);
        collect_battery_entropy(hHash);
        collect_network_entropy(hHash);

        // Finalize this round hash
        status = BCryptFinishHash(hHash, hash, cbHash, 0);
        if (!BCRYPT_SUCCESS(status))
        {
            const NTSTATUS destroyStatus = BCryptDestroyHash(hHash);
            const NTSTATUS closeStatus = BCryptCloseAlgorithmProvider(hAlg, 0);
            (void)destroyStatus;
            (void)closeStatus;
            return 0;
        }

        // Feed hash again for next round if more than 1 round
        if (round + 1 < complexity)
        {
            status = BCryptDestroyHash(hHash);
            if (!BCRYPT_SUCCESS(status))
            {
                const NTSTATUS closeStatus = BCryptCloseAlgorithmProvider(hAlg, 0);
                (void)closeStatus;
                return 0;
            }
            status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
            if (!BCRYPT_SUCCESS(status))
            {
                const NTSTATUS closeStatus = BCryptCloseAlgorithmProvider(hAlg, 0);
                (void)closeStatus;
                return 0;
            }
            const NTSTATUS hashStatus = BCryptHashData(hHash, hash, cbHash, 0);
            if (!BCRYPT_SUCCESS(hashStatus)) {
                const NTSTATUS destroyHashStatus = BCryptDestroyHash(hHash);
                const NTSTATUS closeAlgStatus = BCryptCloseAlgorithmProvider(hAlg, 0);
                (void)destroyHashStatus;
                (void)closeAlgStatus;
                return 0;
            }
        }
    }

    // Generate unique random bytes for the entire buffer
    // First, copy the initial hash block
    DWORD bytesRemaining = (DWORD)size;
    DWORD offset = 0;

    // Copy first block (up to 32 bytes)
    DWORD bytesToCopy = (bytesRemaining < cbHash) ? bytesRemaining : cbHash;
    memcpy(buffer, hash, bytesToCopy);
    bytesRemaining -= bytesToCopy;
    offset += bytesToCopy;

    // For larger buffers, we need to generate additional unique blocks
    if (bytesRemaining > 0) {
        // Create new hash for additional blocks
        status = BCryptDestroyHash(hHash);
        if (!BCRYPT_SUCCESS(status)) {
            BCryptCloseAlgorithmProvider(hAlg, 0);
            return 0;
        }

        // Use counter mode to generate unique blocks
        uint32_t counter = 1; // Start from 1 since we already used block 0

        while (bytesRemaining > 0) {
            status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptCloseAlgorithmProvider(hAlg, 0);
                return 0;
            }

            // Hash the previous output + counter for chaining
            status = BCryptHashData(hHash, hash, cbHash, 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptDestroyHash(hHash);
                BCryptCloseAlgorithmProvider(hAlg, 0);
                return 0;
            }

            status = BCryptHashData(hHash, (PUCHAR)&counter, sizeof(counter), 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptDestroyHash(hHash);
                BCryptCloseAlgorithmProvider(hAlg, 0);
                return 0;
            }

            // Generate next block
            status = BCryptFinishHash(hHash, hash, cbHash, 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptDestroyHash(hHash);
                BCryptCloseAlgorithmProvider(hAlg, 0);
                return 0;
            }

            // Copy to output buffer
            bytesToCopy = (bytesRemaining < cbHash) ? bytesRemaining : cbHash;
            memcpy(buffer + offset, hash, bytesToCopy);
            bytesRemaining -= bytesToCopy;
            offset += bytesToCopy;
            counter++;

            BCryptDestroyHash(hHash);
        }
    }

    BCryptCloseAlgorithmProvider(hAlg, 0);
    return 1;
}

// PUBLIC API

// Returns 1 if RDRAND is supported, else 0
__declspec(dllexport) int test_rng_available(void)
{
    return rdrand_supported() ? 1 : 0;
}

// Returns 1 if threading primitives initialized or initializes now
__declspec(dllexport) int test_threading_available(void)
{
    return InterlockedCompareExchange(&g_threadingInitialized, 0, 0) != 0 ? 1 : 0;
}

// Basic RNG, complexity 1
__declspec(dllexport) int maxrng(unsigned char *buffer, const int size)
{
    if (!buffer || size <= 0) return 0;
    return collect_entropy(buffer, size, 1);
}

// Ultra RNG with complexity param, limits from 1 to 10
__declspec(dllexport) int maxrng_ultra(unsigned char *buffer, const int size, int complexity)
{
    if (!buffer || size <= 0) return 0;
    if (complexity < 1) complexity = 1;
    if (complexity > 10) complexity = 10;
    return collect_entropy(buffer, size, complexity);
}

// Initializes threading primitives if not already done
__declspec(dllexport) void maxrng_init(void)
{
    if (InterlockedCompareExchange(&g_threadingInitialized, 1, 0) == 0) {
        InitializeCriticalSection(&g_rngLock);
    }
}

// Thread-safe version, uses critical section lock
__declspec(dllexport) int maxrng_threadsafe(unsigned char *buffer, const int size)
{
    if (!buffer || size <= 0) return 0;
    EnterCriticalSection(&g_rngLock);
    const int result = collect_entropy(buffer, size, 1);
    LeaveCriticalSection(&g_rngLock);
    return result;
}
