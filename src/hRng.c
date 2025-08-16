#define CRT_SECURE_NO_WARNINGS
#include <windows.h>
#include <intrin.h>
#include <stdint.h>
#include <bcrypt.h>
#include <psapi.h>
#include <iphlpapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")

// ============================================================
// Globals for thread safety
// ============================================================
static CRITICAL_SECTION g_rngLock;
static volatile LONG g_threadingInitialized = 0;

// ============================================================
// Feature enums and config
// ============================================================
typedef enum {
    RNG_HASH_SHA256 = 0,
    RNG_HASH_SHA512 = 1,
    RNG_HASH_SHA1   = 2
} RNG_HASH_ALGO;

typedef enum {
    RNG_EXP_COUNTER = 0,   // Counter-chained rehashing (default)
    RNG_EXP_HKDF    = 1,   // HKDF-Expand using HMAC
    RNG_EXP_HMAC    = 2,   // HMAC(PRK, counter || prev) stream
    RNG_EXP_XOF     = 3    // XOF-like fallback using HMAC stream (no SHAKE)
} RNG_EXP_MODE;

typedef enum {
    RNG_THREAD_NONE     = 0, // lock-free
    RNG_THREAD_CRITSEC  = 1, // use internal critical section
    RNG_THREAD_USERLOCK = 2  // user callbacks
} RNG_THREAD_MODE;

typedef enum {
    RNG_MODE_FAST     = 0,
    RNG_MODE_BALANCED = 1,
    RNG_MODE_SECURE   = 2
} RNG_SECURITY_MODE;

typedef enum {
    RNG_OUT_RAW    = 0,
    RNG_OUT_HEX    = 1,
    RNG_OUT_BASE64 = 2
} RNG_OUTPUT_MODE;

typedef enum {
    RNG_MIX_ROUND_BASED   = 0, // finalize each round then feed
    RNG_MIX_CONTINUOUS    = 1  // one long-running hash, finalize once
} RNG_MIX_MODE;

typedef struct {
    // Entropy source toggles
    int use_cpu;
    int use_rdrand;
    int use_memory;
    int use_perf;
    int use_disk;
    int use_audio;
    int use_battery;
    int use_network;

    // Hash and expansion
    RNG_HASH_ALGO hash_algo;
    RNG_EXP_MODE  expansion;
    RNG_MIX_MODE  mixing;

    // Threading
    RNG_THREAD_MODE threading;
    void (*user_lock)(void);
    void (*user_unlock)(void);

    // Seed injection
    const unsigned char *seed;
    int seed_len;

    // Security preset and custom complexity
    RNG_SECURITY_MODE sec_mode;
    int complexity; // 1..10

    // Output format and desired raw length before encoding
    RNG_OUTPUT_MODE output_mode;

    // Optional HKDF info/context for Expand
    const unsigned char *info;
    int info_len;
} RNG_CONFIG;

// ============================================================
// CPU feature and helpers
// ============================================================
static int rdrand_supported(void) {
    int cpuInfo[4];
    __cpuid(cpuInfo, 1);
    return (cpuInfo[2] & (1 << 30)) != 0;
}

static int rdrand32_retry(uint32_t *val) {
    for (int i = 0; i < 10; i++) {
        if (_rdrand32_step(val))
            return 1;
    }
    return 0;
}

// ============================================================
// Entropy collectors
// ============================================================
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
    HWAVEIN hWaveIn = NULL;
    WAVEFORMATEX wfx = {0};
    wfx.wFormatTag = WAVE_FORMAT_PCM;
    wfx.nChannels = 1;
    wfx.nSamplesPerSec = 8000;
    wfx.wBitsPerSample = 8;
    wfx.nBlockAlign = 1;
    wfx.nAvgBytesPerSec = 8000;
    wfx.cbSize = 0;

    const MMRESULT res = waveInOpen(&hWaveIn, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
    if (res == MMSYSERR_NOERROR && hWaveIn) {
        WAVEHDR hdr = {0};
        BYTE buffer[256] = {0};
        hdr.lpData = (LPSTR)buffer;
        hdr.dwBufferLength = sizeof(buffer);
        hdr.dwFlags = 0;

        if (waveInPrepareHeader(hWaveIn, &hdr, sizeof(hdr)) == MMSYSERR_NOERROR) {
            if (waveInAddBuffer(hWaveIn, &hdr, sizeof(hdr)) == MMSYSERR_NOERROR) {
                if (waveInStart(hWaveIn) == MMSYSERR_NOERROR) {
                    Sleep(50); // Let it capture some audio
                    waveInStop(hWaveIn);
                    BCryptHashData(hHash, buffer, sizeof(buffer), 0);
                }
            }
            waveInUnprepareHeader(hWaveIn, &hdr, sizeof(hdr));
        }
        waveInClose(hWaveIn);
    } else {
        // Fallback: Just hash QueryPerformanceCounter several times with Sleep
        for (int i = 0; i < 5; i++)
        {
            LARGE_INTEGER counter;
            QueryPerformanceCounter(&counter);
            BCryptHashData(hHash, (PUCHAR)&counter, sizeof(counter), 0);
            Sleep(10);
        }
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

// ============================================================
/* Hash provider helpers */
// ============================================================
static LPCWSTR algo_name_from_enum(const RNG_HASH_ALGO a) {
    switch (a) {
        case RNG_HASH_SHA512: return BCRYPT_SHA512_ALGORITHM;
        case RNG_HASH_SHA1:   return BCRYPT_SHA1_ALGORITHM;
        case RNG_HASH_SHA256:
        default:              return BCRYPT_SHA256_ALGORITHM;
    }
}

static DWORD algo_digest_len(const RNG_HASH_ALGO a) {
    switch (a) {
        case RNG_HASH_SHA512: return 64;
        case RNG_HASH_SHA1:   return 20;
        case RNG_HASH_SHA256:
        default:              return 32;
    }
}

// ============================================================
// Base64 and hex utilities
// ============================================================
static int base64_len(const int n) {
    // 4 * ceil(n/3)
    return 4 * ((n + 2) / 3);
}

static int base64_encode(const unsigned char *in, const int in_len, char *out, const int out_len) {
    static const char enc[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    const int needed = base64_len(in_len);
    if (out_len < needed) return 0;

    int i = 0, o = 0;
    while (i + 3 <= in_len) {
        const unsigned v = (in[i] << 16) | (in[i+1] << 8) | in[i+2];
        out[o++] = enc[(v >> 18) & 0x3F];
        out[o++] = enc[(v >> 12) & 0x3F];
        out[o++] = enc[(v >> 6)  & 0x3F];
        out[o++] = enc[v & 0x3F];
        i += 3;
    }
    const int rem = in_len - i;
    if (rem == 1) {
        const unsigned v = (in[i] << 16);
        out[o++] = enc[(v >> 18) & 0x3F];
        out[o++] = enc[(v >> 12) & 0x3F];
        out[o++] = '=';
        out[o++] = '=';
    } else if (rem == 2) {
        const unsigned v = (in[i] << 16) | (in[i+1] << 8);
        out[o++] = enc[(v >> 18) & 0x3F];
        out[o++] = enc[(v >> 12) & 0x3F];
        out[o++] = enc[(v >> 6)  & 0x3F];
        out[o++] = '=';
    }
    return 1;
}

static void hex_encode(const unsigned char *in, const int in_len, char *out) {
    static const char hex[] = "0123456789abcdef";
    for (int i = 0; i < in_len; i++) {
        out[i*2]   = hex[(in[i] >> 4) & 0xF];
        out[i*2+1] = hex[in[i] & 0xF];
    }
}

// ============================================================
// HMAC helpers via BCrypt
// ============================================================
static int hmac_once(const RNG_HASH_ALGO algo,
                     const unsigned char *key, const int key_len,
                     const unsigned char *msg, const int msg_len,
                     unsigned char *out, const DWORD out_len)
{
    BCRYPT_ALG_HANDLE hAlg = NULL;
    BCRYPT_HASH_HANDLE hHash = NULL;
    DWORD cbHash = 0, cbData = 0;

    NTSTATUS s = BCryptOpenAlgorithmProvider(&hAlg, algo_name_from_enum(algo), NULL,
                                             BCRYPT_ALG_HANDLE_HMAC_FLAG);
    if (!BCRYPT_SUCCESS(s)) return 0;

    s = BCryptGetProperty(hAlg, BCRYPT_HASH_LENGTH, (PUCHAR)&cbHash, sizeof(cbHash), &cbData, 0);
    if (!BCRYPT_SUCCESS(s) || cbHash != out_len) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    s = BCryptCreateHash(hAlg, &hHash, NULL, 0, (PUCHAR)key, key_len, 0);
    if (!BCRYPT_SUCCESS(s)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    s = BCryptHashData(hHash, (PUCHAR)msg, msg_len, 0);
    if (!BCRYPT_SUCCESS(s)) { BCryptDestroyHash(hHash); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    s = BCryptFinishHash(hHash, out, cbHash, 0);
    BCryptDestroyHash(hHash);
    BCryptCloseAlgorithmProvider(hAlg, 0);
    return BCRYPT_SUCCESS(s) ? 1 : 0;
}

// HKDF-Extract(salt, IKM) and HKDF-Expand(PRK, info, L)
static int hkdf_extract(const RNG_HASH_ALGO algo,
                        const unsigned char *salt, int salt_len,
                        const unsigned char *ikm, const int ikm_len,
                        unsigned char *prk, const DWORD prk_len)
{
    // If salt is NULL, use all zeros of hash length
    unsigned char zeros[64];
    if (!salt) {
        const DWORD len = algo_digest_len(algo);
        memset(zeros, 0, len);
        salt = zeros;
        salt_len = (int)len;
    }
    return hmac_once(algo, salt, salt_len, ikm, ikm_len, prk, prk_len);
}

static int hkdf_expand(const RNG_HASH_ALGO algo,
                       const unsigned char *prk, const int prk_len,
                       const unsigned char *info, const int info_len,
                       unsigned char *out, const int out_len)
{
    const DWORD hash_len = algo_digest_len(algo);
    unsigned char T[64];
    int t_len = 0;
    int pos = 0;
    unsigned char ctr = 1;

    while (pos < out_len) {
        // T(i) = HMAC(PRK, T(i-1) | info | counter)
        // Build message
        unsigned char msg[64 + 1024 + 1]; // T prev + info + ctr; info_len bounded by int
        int mlen = 0;
        if (t_len > 0) {
            memcpy(msg + mlen, T, t_len);
            mlen += t_len;
        }
        if (info && info_len > 0) {
            memcpy(msg + mlen, info, info_len);
            mlen += info_len;
        }
        msg[mlen++] = ctr;

        if (!hmac_once(algo, prk, prk_len, msg, mlen, T, hash_len)) return 0;

        const int to_copy = (out_len - pos < (int)hash_len) ? (out_len - pos) : (int)hash_len;
        memcpy(out + pos, T, to_copy);
        pos += to_copy;
        t_len = (int)hash_len;
        ctr++;
    }
    return 1;
}

// HMAC-stream expander: out = HMAC(key=PRK, msg=prev || counter)
static int hmac_stream_expand(const RNG_HASH_ALGO algo,
                              const unsigned char *prk, const int prk_len,
                              unsigned char *out, const int out_len)
{
    const DWORD hash_len = algo_digest_len(algo);
    unsigned char prev[64];
    int prev_len = 0;
    int pos = 0;
    unsigned char ctr = 1;

    while (pos < out_len) {
        unsigned char msg[64 + 1];
        int mlen = 0;
        if (prev_len > 0) {
            memcpy(msg, prev, prev_len);
            mlen += prev_len;
        }
        msg[mlen++] = ctr;

        if (!hmac_once(algo, prk, prk_len, msg, mlen, prev, hash_len)) return 0;

        const int to_copy = (out_len - pos < (int)hash_len) ? (out_len - pos) : (int)hash_len;
        memcpy(out + pos, prev, to_copy);
        pos += to_copy;
        prev_len = (int)hash_len;
        ctr++;
    }
    // wipe prev
    SecureZeroMemory(prev, sizeof(prev));
    return 1;
}

// ============================================================
// Entropy aggregation with selectable mixing and sources
// ============================================================
static int hash_update_entropy_from_sources(const BCRYPT_HASH_HANDLE hHash, const RNG_CONFIG *cfg) {
    if (cfg->use_rdrand && rdrand_supported()) {
        uint32_t rndVal = 0;
        if (rdrand32_retry(&rndVal)) {
            BCryptHashData(hHash, (PUCHAR)&rndVal, sizeof(rndVal), 0);
        }
    }
    if (cfg->use_cpu)     collect_cpu_entropy(hHash);
    if (cfg->use_memory)  collect_process_memory_entropy(hHash);
    if (cfg->use_perf)    collect_perf_counter_entropy(hHash);
    if (cfg->use_disk)    collect_disk_entropy(hHash);
    if (cfg->use_audio)   collect_audio_entropy(hHash);
    if (cfg->use_battery) collect_battery_entropy(hHash);
    if (cfg->use_network) collect_network_entropy(hHash);
    return 1;
}

static int collect_entropy_configurable(unsigned char *buffer, const int size, const int rounds,
                                        const RNG_HASH_ALGO algo, const RNG_MIX_MODE mixing,
                                        const RNG_CONFIG *cfg)
{
    BCRYPT_ALG_HANDLE hAlg = NULL;
    BCRYPT_HASH_HANDLE hHash = NULL;
    DWORD cbHash = 0, cbData = 0;
    const DWORD H = algo_digest_len(algo);
    unsigned char digest[64];

    NTSTATUS status = BCryptOpenAlgorithmProvider(&hAlg, algo_name_from_enum(algo), NULL, 0);
    if (!BCRYPT_SUCCESS(status)) return 0;

    status = BCryptGetProperty(hAlg, BCRYPT_HASH_LENGTH, (PUCHAR)&cbHash, sizeof(cbHash), &cbData, 0);
    if (!BCRYPT_SUCCESS(status) || cbHash != H) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

    if (mixing == RNG_MIX_CONTINUOUS) {
        // One long-running hash
        status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
        if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

        for (int i = 0; i < rounds; i++) {
            hash_update_entropy_from_sources(hHash, cfg);
        }
        status = BCryptFinishHash(hHash, digest, cbHash, 0);
        BCryptDestroyHash(hHash);
        if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }
    } else {
        // Round-based finalize then feed digest into next round
        status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
        if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

        for (int round = 0; round < rounds; round++) {
            hash_update_entropy_from_sources(hHash, cfg);
            status = BCryptFinishHash(hHash, digest, cbHash, 0);
            if (!BCRYPT_SUCCESS(status)) {
                BCryptDestroyHash(hHash);
                BCryptCloseAlgorithmProvider(hAlg, 0);
                return 0;
            }
            if (round + 1 < rounds) {
                BCryptDestroyHash(hHash);
                status = BCryptCreateHash(hAlg, &hHash, NULL, 0, NULL, 0, 0);
                if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }
                // feed prior digest to new round
                const NTSTATUS s2 = BCryptHashData(hHash, digest, cbHash, 0);
                if (!BCRYPT_SUCCESS(s2)) {
                    BCryptDestroyHash(hHash);
                    BCryptCloseAlgorithmProvider(hAlg, 0);
                    return 0;
                }
            }
        }
    }

    // Now expand to requested size using counter chaining
    DWORD bytesRemaining = (DWORD)size;
    DWORD offset = 0;

    DWORD bytesToCopy = (bytesRemaining < cbHash) ? bytesRemaining : cbHash;
    memcpy(buffer, digest, bytesToCopy);
    bytesRemaining -= bytesToCopy;
    offset += bytesToCopy;

    if (bytesRemaining > 0) {
        uint32_t counter = 1;
        while (bytesRemaining > 0) {
            BCRYPT_HASH_HANDLE hH = NULL;
            status = BCryptCreateHash(hAlg, &hH, NULL, 0, NULL, 0, 0);
            if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

            status = BCryptHashData(hH, digest, cbHash, 0);
            if (!BCRYPT_SUCCESS(status)) { BCryptDestroyHash(hH); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

            status = BCryptHashData(hH, (PUCHAR)&counter, sizeof(counter), 0);
            if (!BCRYPT_SUCCESS(status)) { BCryptDestroyHash(hH); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

            status = BCryptFinishHash(hH, digest, cbHash, 0);
            BCryptDestroyHash(hH);
            if (!BCRYPT_SUCCESS(status)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

            bytesToCopy = (bytesRemaining < cbHash) ? bytesRemaining : cbHash;
            memcpy(buffer + offset, digest, bytesToCopy);
            bytesRemaining -= bytesToCopy;
            offset += bytesToCopy;
            counter++;
        }
    }

    BCryptCloseAlgorithmProvider(hAlg, 0);
    SecureZeroMemory(digest, sizeof(digest));
    return 1;
}

// ============================================================
// Security presets and threading helpers
// ============================================================

static void apply_security_preset(RNG_CONFIG *cfg) {
    switch (cfg->sec_mode) {
        case RNG_MODE_FAST:
            cfg->use_audio = 0;
            cfg->use_network = 0;
            cfg->use_disk = 0;
            cfg->hash_algo = RNG_HASH_SHA256;
            if (cfg->complexity < 1) cfg->complexity = 1;
            cfg->mixing = RNG_MIX_CONTINUOUS;
            break;
        case RNG_MODE_SECURE:
            cfg->use_audio = 1;
            cfg->use_network = 1;
            cfg->use_disk = 1;
            cfg->hash_algo = RNG_HASH_SHA512;
            if (cfg->complexity < 3) cfg->complexity = 3;
            cfg->mixing = RNG_MIX_ROUND_BASED;
            break;
        case RNG_MODE_BALANCED:
        default:
            cfg->use_audio = 1;
            cfg->use_network = 1;
            cfg->use_disk = 1;
            cfg->hash_algo = (cfg->hash_algo == RNG_HASH_SHA256 || cfg->hash_algo == RNG_HASH_SHA1)
                             ? cfg->hash_algo : RNG_HASH_SHA256;
            if (cfg->complexity < 2) cfg->complexity = 2;
            cfg->mixing = RNG_MIX_CONTINUOUS;
            break;
    }
}

static int ensure_threading_enter(const RNG_CONFIG *cfg) {
    if (cfg->threading == RNG_THREAD_CRITSEC) {
        EnterCriticalSection(&g_rngLock);
    } else if (cfg->threading == RNG_THREAD_USERLOCK && cfg->user_lock) {
        cfg->user_lock();
    }
    return 1;
}

static void ensure_threading_leave(const RNG_CONFIG *cfg) {
    if (cfg->threading == RNG_THREAD_CRITSEC) {
        LeaveCriticalSection(&g_rngLock);
    } else if (cfg->threading == RNG_THREAD_USERLOCK && cfg->user_unlock) {
        cfg->user_unlock();
    }
}

// Core expand dispatcher
static int expand_output(const RNG_CONFIG *cfg,
                         const unsigned char *ikm, const int ikm_len,
                         unsigned char *out_raw, const int out_len)
{
    if (ikm_len <= 0) return 0;

    const RNG_HASH_ALGO algo = cfg->hash_algo;
    const DWORD H = algo_digest_len(algo);

    // If seed present and expansion uses HMAC or HKDF, treat seed as salt or key
    switch (cfg->expansion) {
        case RNG_EXP_COUNTER: {
            // Use counter chaining starting from IKM digest blocks
            // Implement using H = hash_len blocks: hash(ikm || counter)
            BCRYPT_ALG_HANDLE hAlg = NULL;
            BCRYPT_HASH_HANDLE hH = NULL;
            DWORD cbHash = 0, cbData = 0;
            unsigned char block[64];
            uint32_t ctr = 1;
            int pos = 0;

            NTSTATUS s = BCryptOpenAlgorithmProvider(&hAlg, algo_name_from_enum(algo), NULL, 0);
            if (!BCRYPT_SUCCESS(s)) return 0;

            s = BCryptGetProperty(hAlg, BCRYPT_HASH_LENGTH, (PUCHAR)&cbHash, sizeof(cbHash), &cbData, 0);
            if (!BCRYPT_SUCCESS(s) || cbHash != H) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

            while (pos < out_len) {
                s = BCryptCreateHash(hAlg, &hH, NULL, 0, NULL, 0, 0);
                if (!BCRYPT_SUCCESS(s)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

                s = BCryptHashData(hH, (PUCHAR)ikm, ikm_len, 0);
                if (!BCRYPT_SUCCESS(s)) { BCryptDestroyHash(hH); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

                if (cfg->seed && cfg->seed_len > 0) {
                    // fold seed for domain separation
                    s = BCryptHashData(hH, (PUCHAR)cfg->seed, cfg->seed_len, 0);
                    if (!BCRYPT_SUCCESS(s)) { BCryptDestroyHash(hH); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }
                }

                s = BCryptHashData(hH, (PUCHAR)&ctr, sizeof(ctr), 0);
                if (!BCRYPT_SUCCESS(s)) { BCryptDestroyHash(hH); BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

                s = BCryptFinishHash(hH, block, H, 0);
                BCryptDestroyHash(hH);
                if (!BCRYPT_SUCCESS(s)) { BCryptCloseAlgorithmProvider(hAlg, 0); return 0; }

                const int to_copy = (out_len - pos < (int)H) ? (out_len - pos) : (int)H;
                memcpy(out_raw + pos, block, to_copy);
                pos += to_copy;
                ctr++;
            }
            BCryptCloseAlgorithmProvider(hAlg, 0);
            SecureZeroMemory(block, sizeof(block));
            return 1;
        }
        case RNG_EXP_HKDF: {
            unsigned char prk[64];
            if (!hkdf_extract(algo,
                              cfg->seed, cfg->seed_len,   // salt
                              ikm, ikm_len,              // IKM
                              prk, H)) return 0;

            const int ok = hkdf_expand(algo, prk, (int)H, cfg->info, cfg->info_len, out_raw, out_len);
            SecureZeroMemory(prk, sizeof(prk));
            return ok;
        }
        case RNG_EXP_HMAC: {
            // Treat seed as the HMAC key. If not provided, use IKM as key and seed as data
            const unsigned char *key = cfg->seed ? cfg->seed : ikm;
            const int key_len = cfg->seed ? cfg->seed_len : ikm_len;

            // Produce a stream
            return hmac_stream_expand(algo, key, key_len, out_raw, out_len);
        }
        case RNG_EXP_XOF: {
            // Fallback XOF using HKDF-Extract with seed (optional) and HKDF-Expand indefinitely
            unsigned char prk[64];
            if (!hkdf_extract(algo,
                              cfg->seed, cfg->seed_len,
                              ikm, ikm_len,
                              prk, H)) return 0;
            const int ok = hkdf_expand(algo, prk, (int)H, cfg->info, cfg->info_len, out_raw, out_len);
            SecureZeroMemory(prk, sizeof(prk));
            return ok;
        }
        default:
            return 0;
    }
}


// ============================================================
// PUBLIC API
// ============================================================

// Returns 1 if RDRAND is supported, else 0
__declspec(dllexport) int test_rng_available(void) {
    return rdrand_supported() ? 1 : 0;
}

// Returns 1 if threading primitives initialized or initializes now
__declspec(dllexport) int test_threading_available(void) {
    return InterlockedCompareExchange(&g_threadingInitialized, 0, 0) != 0 ? 1 : 0;
}

// Basic RNG, complexity 1
__declspec(dllexport) int maxrng(unsigned char *buffer, const int size) {
    if (!buffer || size <= 0) return 0;

    RNG_CONFIG cfg = {0};
    cfg.use_cpu = cfg.use_memory = cfg.use_perf = cfg.use_disk =
                                                  cfg.use_audio = cfg.use_battery = cfg.use_network = 1;
    cfg.use_rdrand = 1;
    cfg.hash_algo = RNG_HASH_SHA256;
    cfg.mixing = RNG_MIX_ROUND_BASED;
    cfg.expansion = RNG_EXP_COUNTER;
    cfg.threading = RNG_THREAD_NONE;
    cfg.sec_mode = RNG_MODE_BALANCED;
    cfg.complexity = 1;
    cfg.output_mode = RNG_OUT_RAW;

    return collect_entropy_configurable(buffer, size, 1, cfg.hash_algo, cfg.mixing, &cfg);
}

// Ultra RNG with complexity param, limits from 1 to 10
__declspec(dllexport) int maxrng_ultra(unsigned char *buffer, const int size, int complexity) {
    if (!buffer || size <= 0) return 0;
    if (complexity < 1) complexity = 1;
    if (complexity > 10) complexity = 10;

    RNG_CONFIG cfg = {0};
    cfg.use_cpu = cfg.use_memory = cfg.use_perf = cfg.use_disk =
                                                  cfg.use_audio = cfg.use_battery = cfg.use_network = 1;
    cfg.use_rdrand = 1;
    cfg.hash_algo = RNG_HASH_SHA512; // be generous for ultra
    cfg.mixing = RNG_MIX_ROUND_BASED;
    cfg.expansion = RNG_EXP_COUNTER;
    cfg.threading = RNG_THREAD_NONE;
    cfg.sec_mode = RNG_MODE_SECURE;
    cfg.complexity = complexity;
    cfg.output_mode = RNG_OUT_RAW;

    return collect_entropy_configurable(buffer, size, complexity, cfg.hash_algo, cfg.mixing, &cfg);
}

// Initializes threading primitives if not already done
__declspec(dllexport) void maxrng_init(void) {
    if (InterlockedCompareExchange(&g_threadingInitialized, 1, 0) == 0) {
        InitializeCriticalSection(&g_rngLock);
    }
}

// Thread-safe version, uses critical section lock, with optional complexity param (default 1)
__declspec(dllexport) int maxrng_threadsafe(unsigned char *buffer, const int size, int complexity) {
    if (!buffer || size <= 0) return 0;
    if (complexity < 1) complexity = 1;
    if (complexity > 5) complexity = 5;
    EnterCriticalSection(&g_rngLock);

    RNG_CONFIG cfg = {0};
    cfg.use_cpu = cfg.use_memory = cfg.use_perf = cfg.use_disk =
                                                  cfg.use_audio = cfg.use_battery = cfg.use_network = 1;
    cfg.use_rdrand = 1;
    cfg.hash_algo = RNG_HASH_SHA256;
    cfg.mixing = RNG_MIX_CONTINUOUS;
    cfg.expansion = RNG_EXP_COUNTER;
    cfg.threading = RNG_THREAD_CRITSEC;
    cfg.sec_mode = RNG_MODE_BALANCED;
    cfg.complexity = complexity;
    cfg.output_mode = RNG_OUT_RAW;

    const int result = collect_entropy_configurable(buffer, size, complexity, cfg.hash_algo, cfg.mixing, &cfg);
    LeaveCriticalSection(&g_rngLock);
    return result;
}

// Core DEV RNG with configurable options
__declspec(dllexport)
int maxrng_dev(unsigned char *out_buf, const int out_buf_len, const int raw_len, const RNG_CONFIG *cfg_in)
{
    if (!out_buf || out_buf_len <= 0 || raw_len <= 0 || !cfg_in) return 0;

    RNG_CONFIG cfg = *cfg_in;

    // Reasonable defaults if caller forgot toggles
    if (!(cfg.use_cpu | cfg.use_memory | cfg.use_perf | cfg.use_disk |
          cfg.use_audio | cfg.use_battery | cfg.use_network | cfg.use_rdrand))
    {
        cfg.use_cpu = cfg.use_memory = cfg.use_perf = 1;
        cfg.use_disk = cfg.use_audio = cfg.use_battery = cfg.use_network = 1;
        cfg.use_rdrand = 1;
    }

    // Apply security preset
    apply_security_preset(&cfg);

    // Clamp complexity
    if (cfg.complexity < 1) cfg.complexity = 1;
    if (cfg.complexity > 10) cfg.complexity = 10;

    // Validate output buffer for the requested output mode
    int needed = 0;
    switch (cfg.output_mode) {
        case RNG_OUT_RAW:    needed = raw_len; break;
        case RNG_OUT_HEX:    needed = raw_len * 2; break;
        case RNG_OUT_BASE64: needed = base64_len(raw_len); break;
        default: return 0;
    }
    if (out_buf_len < needed) return 0;

    // Allocate raw workspace
    unsigned char *raw = (unsigned char*)malloc((size_t)raw_len);
    if (!raw) return 0;

    // Threading
    ensure_threading_enter(&cfg);

    // 1) Gather entropy into intermediate digest material using selected mixing
    // Use collect_entropy_configurable to produce a base digest of size raw_len at least as input keying material
    // For better domain separation, derive ikm_len = max(H, min(raw_len, 2*H))
    const DWORD H = algo_digest_len(cfg.hash_algo);
    const int ikm_len = (raw_len < (int)H) ? (int)H : ((raw_len > (int)(H * 2)) ? (int)(H * 2) : raw_len);

    unsigned char *ikm = (unsigned char*)malloc((size_t)ikm_len);
    if (!ikm) {
        ensure_threading_leave(&cfg);
        free(raw);
        return 0;
    }
    if (!collect_entropy_configurable(ikm, ikm_len, cfg.complexity, cfg.hash_algo, cfg.mixing, &cfg)) {
        ensure_threading_leave(&cfg);
        free(ikm);
        free(raw);
        return 0;
    }

    // Seed injection for non HMAC/HKDF modes: fold by XOR to avoid bias
    if ((cfg.expansion == RNG_EXP_COUNTER || cfg.expansion == RNG_EXP_XOF) && cfg.seed && cfg.seed_len > 0) {
        const int m = (cfg.seed_len < ikm_len) ? cfg.seed_len : ikm_len;
        for (int i = 0; i < m; i++) ikm[i] ^= cfg.seed[i];
    }

    // 2) Expand according to selected strategy into raw
    int ok = expand_output(&cfg, ikm, ikm_len, raw, raw_len);

    // Wipe ikm and release
    SecureZeroMemory(ikm, (size_t)ikm_len);
    free(ikm);

    // 3) Write in requested output format
    if (ok) {
        if (cfg.output_mode == RNG_OUT_RAW) {
            memcpy(out_buf, raw, raw_len);
        } else if (cfg.output_mode == RNG_OUT_HEX) {
            hex_encode(raw, raw_len, (char*)out_buf);
        } else if (cfg.output_mode == RNG_OUT_BASE64) {
            ok = base64_encode(raw, raw_len, (char*)out_buf, out_buf_len);
        } else {
            ok = 0;
        }
    }

    // Wipe raw and leave
    SecureZeroMemory(raw, (size_t)raw_len);
    free(raw);
    ensure_threading_leave(&cfg);

    return ok ? needed : 0; // return number of bytes written, or 0 on failure
}

// Convenience: sane defaults helper
__declspec(dllexport)
void maxrng_dev_default_config(RNG_CONFIG *cfg, const RNG_SECURITY_MODE mode) {
    if (!cfg) return;
    memset(cfg, 0, sizeof(*cfg));
    cfg->use_cpu = cfg->use_memory = cfg->use_perf = cfg->use_disk =
    cfg->use_audio = cfg->use_battery = cfg->use_network = 1;
    cfg->use_rdrand = 1;

    cfg->hash_algo = RNG_HASH_SHA256;
    cfg->expansion = RNG_EXP_COUNTER;
    cfg->mixing = RNG_MIX_CONTINUOUS;
    cfg->threading = RNG_THREAD_NONE;
    cfg->sec_mode = mode;
    cfg->complexity = 2;
    cfg->output_mode = RNG_OUT_RAW;
    cfg->info = NULL;
    cfg->info_len = 0;

    apply_security_preset(cfg);
}
