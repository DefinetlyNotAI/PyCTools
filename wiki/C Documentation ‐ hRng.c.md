# Hardware Random Number Generator (hRng)

A high-quality random number generation library designed for Windows systems, combining multiple entropy sources with cryptographic processing.

## Overview

The hRng module provides cryptographically secure random number generation using a hybrid approach that combines:

- Hardware-based entropy (Intel RDRAND when available)
- System-based entropy from various Windows subsystems
- Cryptographic processing via Windows BCrypt API

This combination ensures high-quality random numbers even when hardware RNG is unavailable or potentially compromised.

## Features

- **Multiple Entropy Sources**:
  - CPU features (RDRAND, RDTSC, CPUID)
  - Memory statistics
  - Performance counters
  - Disk usage metrics
  - Audio sampling
  - Battery status
  - Network statistics

- **Security Options**:
  - Configurable complexity levels (1-10)
  - Multiple hash algorithms (SHA-256, SHA-512, SHA-1)
  - Various expansion modes (Counter, HKDF, HMAC, XOF)
  - Different mixing strategies

- **Thread Safety**:
  - Built-in critical section support
  - Optional user-provided synchronization

- **Output Flexibility**:
  - Raw binary output
  - Hexadecimal encoding
  - Base64 encoding

## Basic API

### Check RDRAND Availability

```c
int test_rng_available(void);
```

**Returns:**
- `1` if the CPU supports RDRAND
- `0` if RDRAND is not available

### Basic Random Number Generation

```c
int maxrng(unsigned char *buffer, const int size);
```

**Parameters:**
- `buffer`: Pointer to buffer to be filled with random bytes
- `size`: Number of bytes to generate

**Returns:**
- `1` on success
- `0` on failure

### Thread-Safety Initialization

```c
void maxrng_init(void);
```

Initializes internal critical section for thread-safe operation. Must be called before using thread-safe functions.

### Thread-Safe Random Generation

```c
int maxrng_threadsafe(unsigned char *buffer, const int size, int complexity);
```

**Parameters:**
- `buffer`: Pointer to buffer to be filled with random bytes
- `size`: Number of bytes to generate
- `complexity`: Level of entropy gathering (1-5, default 1)

**Returns:**
- `1` on success
- `0` on failure

### Enhanced Security Random Generation

```c
int maxrng_ultra(unsigned char *buffer, const int size, int complexity);
```

**Parameters:**
- `buffer`: Pointer to buffer to be filled with random bytes
- `size`: Number of bytes to generate
- `complexity`: Level of entropy gathering intensity (1-10)

**Returns:**
- `1` on success
- `0` on failure

## Advanced API

### Configurable Random Generation

```c
int maxrng_dev(unsigned char *out_buf, const int out_buf_len, 
               const int raw_len, const RNG_CONFIG *cfg_in);
```

**Parameters:**
- `out_buf`: Pointer to output buffer
- `out_buf_len`: Size of output buffer
- `raw_len`: Requested raw bytes to generate
- `cfg_in`: Pointer to configuration structure

**Returns:**
- Number of bytes written on success
- `0` on failure

### Configuration Helper

```c
void maxrng_dev_default_config(RNG_CONFIG *cfg, const RNG_SECURITY_MODE mode);
```

**Parameters:**
- `cfg`: Pointer to configuration structure to initialize
- `mode`: Security mode preset to apply

## Configuration Structure

```c
typedef struct {
    // Entropy source toggles
    int use_cpu;       // CPU info and timing
    int use_rdrand;    // Intel RDRAND instruction 
    int use_memory;    // Process memory statistics
    int use_perf;      // Performance counters
    int use_disk;      // Disk usage metrics
    int use_audio;     // Audio timing entropy
    int use_battery;   // Power status information
    int use_network;   // Network adapter statistics

    // Hash and expansion configuration
    RNG_HASH_ALGO hash_algo;  // SHA-256, SHA-512, or SHA-1
    RNG_EXP_MODE  expansion;  // How to expand entropy into output
    RNG_MIX_MODE  mixing;     // How to mix entropy sources

    // Threading configuration
    RNG_THREAD_MODE threading; // Thread safety approach
    void (*user_lock)(void);   // User-provided lock function
    void (*user_unlock)(void); // User-provided unlock function

    // External seed injection
    const unsigned char *seed; // Optional external seed material
    int seed_len;              // Length of seed

    // Security level
    RNG_SECURITY_MODE sec_mode; // Security preset
    int complexity;             // Complexity level (1-10)

    // Output configuration
    RNG_OUTPUT_MODE output_mode; // Raw, hex, or base64

    // HKDF context (optional)
    const unsigned char *info;   // Info string for HKDF
    int info_len;                // Length of info string
} RNG_CONFIG;
```

## Enumeration Types

### Hash Algorithms

```c
typedef enum {
    RNG_HASH_SHA256 = 0, // SHA-256 (default)
    RNG_HASH_SHA512 = 1, // SHA-512 (stronger)
    RNG_HASH_SHA1   = 2  // SHA-1 (legacy, not recommended)
} RNG_HASH_ALGO;
```

### Expansion Modes

```c
typedef enum {
    RNG_EXP_COUNTER = 0, // Counter-chained rehashing (default)
    RNG_EXP_HKDF    = 1, // HKDF-Expand using HMAC
    RNG_EXP_HMAC    = 2, // HMAC(PRK, counter || prev) stream
    RNG_EXP_XOF     = 3  // XOF-like output using HMAC stream
} RNG_EXP_MODE;
```

### Threading Modes

```c
typedef enum {
    RNG_THREAD_NONE     = 0, // No synchronization
    RNG_THREAD_CRITSEC  = 1, // Use internal critical section
    RNG_THREAD_USERLOCK = 2  // Use user-provided callbacks
} RNG_THREAD_MODE;
```

### Security Modes

```c
typedef enum {
    RNG_MODE_FAST     = 0, // Faster but less intensive gathering
    RNG_MODE_BALANCED = 1, // Balanced speed and security (default)
    RNG_MODE_SECURE   = 2  // Maximum security, slower
} RNG_SECURITY_MODE;
```

### Output Modes

```c
typedef enum {
    RNG_OUT_RAW    = 0, // Raw binary output
    RNG_OUT_HEX    = 1, // Hexadecimal encoded string
    RNG_OUT_BASE64 = 2  // Base64 encoded string
} RNG_OUTPUT_MODE;
```

### Mixing Modes

```c
typedef enum {
    RNG_MIX_ROUND_BASED = 0, // Finalize each round then feed
    RNG_MIX_CONTINUOUS  = 1  // One long-running hash, finalize once
} RNG_MIX_MODE;
```

## Usage Examples

### Basic Usage

```c
#include <stdio.h>
#include <windows.h>

typedef int (*MaxRNG_Func)(unsigned char*, int);

int main() {
    HMODULE hDll = LoadLibrary("hRng.dll");
    if (!hDll) {
        printf("Failed to load hRng.dll\n");
        return 1;
    }
    
    MaxRNG_Func rng = (MaxRNG_Func)GetProcAddress(hDll, "maxrng");
    if (!rng) {
        printf("Failed to get function address\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    unsigned char buffer[32] = {0};
    if (rng(buffer, sizeof(buffer))) {
        printf("Random bytes generated:\n");
        for (int i = 0; i < sizeof(buffer); i++) {
            printf("%02X ", buffer[i]);
        }
        printf("\n");
    } else {
        printf("Failed to generate random bytes\n");
    }
    
    FreeLibrary(hDll);
    return 0;
}
```

### Thread-Safe Usage

```c
#include <stdio.h>
#include <windows.h>

typedef void (*Init_Func)(void);
typedef int (*ThreadSafe_RNG_Func)(unsigned char*, int, int);

DWORD WINAPI ThreadFunc(LPVOID lpParam) {
    ThreadSafe_RNG_Func rng = (ThreadSafe_RNG_Func)lpParam;
    
    unsigned char buffer[16] = {0};
    if (rng(buffer, sizeof(buffer), 2)) { // Complexity level 2
        printf("Thread %lu: Success\n", GetCurrentThreadId());
    } else {
        printf("Thread %lu: Failed\n", GetCurrentThreadId());
    }
    
    return 0;
}

int main() {
    HMODULE hDll = LoadLibrary("hRng.dll");
    if (!hDll) return 1;
    
    Init_Func init = (Init_Func)GetProcAddress(hDll, "maxrng_init");
    ThreadSafe_RNG_Func tsRng = (ThreadSafe_RNG_Func)GetProcAddress(hDll, "maxrng_threadsafe");
    
    if (!init || !tsRng) {
        FreeLibrary(hDll);
        return 1;
    }
    
    // Initialize threading support
    init();
    
    // Create multiple threads
    HANDLE threads[5];
    for (int i = 0; i < 5; i++) {
        threads[i] = CreateThread(NULL, 0, ThreadFunc, (LPVOID)tsRng, 0, NULL);
    }
    
    WaitForMultipleObjects(5, threads, TRUE, INFINITE);
    
    for (int i = 0; i < 5; i++) {
        CloseHandle(threads[i]);
    }
    
    FreeLibrary(hDll);
    return 0;
}
```

### Advanced Configuration

```c
#include <stdio.h>
#include <windows.h>
#include <string.h>

// Define the required types
typedef enum {
    RNG_HASH_SHA256 = 0,
    RNG_HASH_SHA512 = 1,
    RNG_HASH_SHA1   = 2
} RNG_HASH_ALGO;

typedef enum {
    RNG_EXP_COUNTER = 0,
    RNG_EXP_HKDF    = 1,
    RNG_EXP_HMAC    = 2,
    RNG_EXP_XOF     = 3
} RNG_EXP_MODE;

typedef enum {
    RNG_THREAD_NONE     = 0,
    RNG_THREAD_CRITSEC  = 1,
    RNG_THREAD_USERLOCK = 2
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
    RNG_MIX_ROUND_BASED = 0,
    RNG_MIX_CONTINUOUS  = 1
} RNG_MIX_MODE;

typedef struct {
    int use_cpu;
    int use_rdrand;
    int use_memory;
    int use_perf;
    int use_disk;
    int use_audio;
    int use_battery;
    int use_network;

    RNG_HASH_ALGO hash_algo;
    RNG_EXP_MODE  expansion;
    RNG_MIX_MODE  mixing;

    RNG_THREAD_MODE threading;
    void (*user_lock)(void);
    void (*user_unlock)(void);

    const unsigned char *seed;
    int seed_len;

    RNG_SECURITY_MODE sec_mode;
    int complexity;

    RNG_OUTPUT_MODE output_mode;

    const unsigned char *info;
    int info_len;
} RNG_CONFIG;

// Function types
typedef void (*DefaultConfig_Func)(RNG_CONFIG*, RNG_SECURITY_MODE);
typedef int (*DevRNG_Func)(unsigned char*, int, int, const RNG_CONFIG*);

int main() {
    HMODULE hDll = LoadLibrary("hRng.dll");
    if (!hDll) return 1;
    
    DefaultConfig_Func getDefaultConfig = 
        (DefaultConfig_Func)GetProcAddress(hDll, "maxrng_dev_default_config");
    DevRNG_Func devRng = 
        (DevRNG_Func)GetProcAddress(hDll, "maxrng_dev");
    
    if (!getDefaultConfig || !devRng) {
        FreeLibrary(hDll);
        return 1;
    }
    
    // Get default secure configuration
    RNG_CONFIG cfg;
    getDefaultConfig(&cfg, RNG_MODE_SECURE);
    
    // Customize the configuration
    cfg.hash_algo = RNG_HASH_SHA512;
    cfg.complexity = 5;
    cfg.output_mode = RNG_OUT_HEX;
    
    // Generate 16 bytes (32 hex chars)
    char hexOutput[33] = {0};
    int bytesWritten = devRng((unsigned char*)hexOutput, 33, 16, &cfg);
    
    if (bytesWritten > 0) {
        printf("Random hex string: %s\n", hexOutput);
    } else {
        printf("Failed to generate random data\n");
    }
    
    FreeLibrary(hDll);
    return 0;
}
```

## Implementation Details

### Entropy Collection

The library collects entropy from a variety of sources to ensure high-quality randomness:

1. **Hardware RNG**: Uses Intel's RDRAND instruction if available, with retry logic for reliability.

2. **CPU Information**: Collects CPU information via CPUID instruction and high-resolution timestamp counter (RDTSC).

3. **Process Memory**: Gathers information about current process memory usage and statistics.

4. **Performance Metrics**: Uses high-resolution performance counters for timing-based entropy.

5. **Disk Information**: Collects disk space statistics from the system drive.

6. **Audio Sampling**: Attempts to sample audio input or falls back to timing-based collection when audio hardware is unavailable.

7. **Battery Status**: Retrieves power and battery information from the system.

8. **Network Statistics**: Collects TCP/IP statistics and network adapter information.

### Entropy Mixing

Collected entropy is mixed using cryptographic hash functions via the Windows BCrypt API:

- **Round-Based Mixing**: Each source of entropy is hashed separately, then the digests are combined.
- **Continuous Mixing**: All entropy sources are fed into a single hash context and finalized once.

### Expansion Methods

The library supports several methods to expand a small entropy pool into a larger output:

1. **Counter-Chaining**: Uses a counter with the entropy material to generate additional blocks.
2. **HKDF**: Uses the HMAC-based Key Derivation Function to expand the entropy.
3. **HMAC Stream**: Creates a stream of HMAC outputs using previous outputs and counters.
4. **XOF-like**: Implements an extendable-output function approach using HMAC.

### Security Modes

Three security presets are available:

1. **Fast Mode**:
   - Uses SHA-256
   - Minimal complexity (1)
   - Skips slow entropy sources
   - Uses continuous mixing

2. **Balanced Mode**:
   - Uses SHA-256
   - Medium complexity (2)
   - Includes all entropy sources
   - Uses continuous mixing

3. **Secure Mode**:
   - Uses SHA-512
   - Higher complexity (3+)
   - Includes all entropy sources
   - Uses round-based mixing for better domain separation

## Technical Considerations

### Thread Safety

The library offers three threading modes:

1. **No Synchronization**: For single-threaded applications or when the caller handles synchronization.
2. **Critical Section**: Uses an internal Windows critical section for thread safety.
3. **User Callbacks**: Allows the caller to provide custom lock/unlock functions.

### Performance vs. Security

The complexity parameter directly affects both security and performance:

- **Low Complexity (1-2)**: Suitable for non-critical applications, faster generation
- **Medium Complexity (3-5)**: Good balance for most security-sensitive applications
- **High Complexity (6-10)**: Maximum security for cryptographic key generation

### Memory Safety

The library follows best practices for cryptographic implementations:

- Sensitive buffers are cleared using `SecureZeroMemory` after use
- Proper error handling with resource cleanup
- Bounds checking on all buffer operations

## Dependencies

The library depends on the following Windows components:

- **BCrypt API**: For cryptographic hashing operations
- **Windows Performance API**: For high-resolution timing
- **Windows Multimedia API**: For audio sampling
- **IP Helper API**: For network statistics
- **Process Status API**: For memory information

When linking to the DLL, these dependencies are automatically resolved.

## Building

The library is built using the following compile-time options:

```c
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")
```
