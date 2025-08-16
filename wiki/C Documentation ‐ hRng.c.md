# Hardware Random Number Generator (hRng)

The `/dev/urandom/` of Windows.

---

<details>
<summary>Outdated documentation for v1.0.0 - hRng.c</summary>

## hRng.c

Implements a hardware random number generator using the RDRAND instruction (if supported by the CPU).

### Key Function
- `int read_hwrng(unsigned char* buffer, int size)`
    - Fills `buffer` with `size` random bytes from the hardware RNG.
    - Returns 1 on success, 0 if RDRAND is not supported or fails.
    - Exported for use by Python via ctypes.

### Notes
- Checks for RDRAND support using CPUID.
- Used by `pyCTools.hwrng`.
</details>

---

## Overview

The Hardware Random Number Generator (hRng) is a high-security random number generation library designed for Windows systems. It provides cryptographically secure random numbers by combining multiple entropy sources with hardware-based random number generation when available.

## Key Features

- Hardware-accelerated random number generation using Intel RDRAND instruction (when available)
- Multiple entropy sources for enhanced security:
  - CPU-specific entropy (RDTSC, CPUID)
  - System performance metrics (timing, memory usage)
  - Process memory information
  - Disk space statistics
  - Network adapter and TCP statistics
  - Battery and power status information
- Secure entropy mixing using SHA-256 via Windows BCrypt API
- Thread-safe operation with proper synchronization
- Configurable complexity levels for enhanced security
- Fallback mechanisms when hardware RNG is unavailable

## API Reference

### `int test_rng_available(void)`
Detects if the CPU supports the RDRAND instruction.

**Returns:**
- `1` if RDRAND is supported
- `0` if RDRAND is not supported

### `int test_threading_available(void)`
Checks if threading primitives are initialized.

**Returns:**
- `1` if threading primitives are initialized
- `0` otherwise

### `int maxrng(unsigned char* buffer, const int size)`
The primary RNG function that combines multiple entropy sources with basic complexity.

**Parameters:**
- `buffer`: Pointer to the buffer to fill with random bytes
- `size`: Number of bytes to generate

**Returns:**
- `1` on success
- `0` on failure

### `void maxrng_init(void)`
Initializes threading primitives for thread-safe operation.
This function must be called before using the thread-safe RNG functions.

If not called, the thread-safe RNG functions will not work correctly (crashing with invalid pointer errors).

> `test_threading_available` will always return `0` if this function has not been called.

**Returns:**
- None

### `int maxrng_threadsafe(unsigned char* buffer, const int size)`
Thread-safe wrapper for the RNG function.

**Parameters:**
- `buffer`: Pointer to the buffer to fill with random bytes
- `size`: Number of bytes to generate

**Returns:**
- `1` on success
- `0` on failure

### `int maxrng_ultra(unsigned char* buffer, const int size, int complexity)`
Enhanced random number generation with configurable complexity level.

**Parameters:**
- `buffer`: Pointer to the buffer to fill with random bytes
- `size`: Number of bytes to generate
- `complexity`: Level of entropy gathering intensity (1-10):
  - Higher values increase the number of entropy gathering rounds
  - Values are automatically clamped between 1 and 10

**Returns:**
- `1` on success
- `0` on failure

## Usage Examples

> [!IMPORTANT]
> The following examples have not been tested in `C` - but the DLL worked in `Python` so minor tweaks should fix any issues in the provided examples.

### Basic Usage

```c
#include <stdio.h>
#include <windows.h>

// Import the DLL functions
typedef int (*MaxRNG_Func)(unsigned char*, int);
typedef int (*RngAvailable_Func)(void);

int main() {
    // Load the DLL
    HMODULE hRngDll = LoadLibrary("hRng.dll");
    if (!hRngDll) {
        printf("Failed to load hRng.dll\n");
        return 1;
    }
    
    // Get function pointers
    MaxRNG_Func rng = (MaxRNG_Func)GetProcAddress(hRngDll, "maxrng");
    RngAvailable_Func rngAvailable = (RngAvailable_Func)GetProcAddress(hRngDll, "test_rng_available");
    
    if (!rng || !rngAvailable) {
        printf("Failed to get function addresses\n");
        FreeLibrary(hRngDll);
        return 1;
    }
    
    // Check if hardware RNG is available
    printf("Hardware RNG available: %s\n", rngAvailable() ? "Yes" : "No");
    
    // Generate random bytes
    unsigned char buffer[32] = {0};
    if (rng(buffer, sizeof(buffer))) {
        printf("Random bytes generated successfully:\n");
        for (int i = 0; i < sizeof(buffer); i++) {
            printf("%02X ", buffer[i]);
        }
        printf("\n");
    } else {
        printf("Failed to generate random bytes\n");
    }
    
    FreeLibrary(hRngDll);
    return 0;
}
```

### Thread-Safe Usage

```c
#include <windows.h>
#include <stdio.h>

// Import the DLL functions
typedef void (*Init_Func)(void);
typedef int (*ThreadSafe_RNG_Func)(unsigned char*, int);

DWORD WINAPI ThreadFunc(LPVOID lpParam) {
    ThreadSafe_RNG_Func rng = (ThreadSafe_RNG_Func)lpParam;
    
    unsigned char buffer[16] = {0};
    int result = rng(buffer, sizeof(buffer));
    
    // Print thread ID and result
    printf("Thread %lu: %s\n", GetCurrentThreadId(), 
           result ? "Success" : "Failed");
           
    return 0;
}

int main() {
    HMODULE hRngDll = LoadLibrary("hRng.dll");
    if (!hRngDll) {
        printf("Failed to load hRng.dll\n");
        return 1;
    }
    
    Init_Func init = (Init_Func)GetProcAddress(hRngDll, "maxrng_init");
    ThreadSafe_RNG_Func threadSafeRng = 
        (ThreadSafe_RNG_Func)GetProcAddress(hRngDll, "maxrng_threadsafe");
    
    if (!init || !threadSafeRng) {
        printf("Failed to get function addresses\n");
        FreeLibrary(hRngDll);
        return 1;
    }
    
    // Initialize threading primitives
    init();
    
    // Create multiple threads to test thread safety
    HANDLE threads[5];
    for (int i = 0; i < 5; i++) {
        threads[i] = CreateThread(NULL, 0, ThreadFunc, 
                                 (LPVOID)threadSafeRng, 0, NULL);
    }
    
    // Wait for all threads to complete
    WaitForMultipleObjects(5, threads, TRUE, INFINITE);
    
    for (int i = 0; i < 5; i++) {
        CloseHandle(threads[i]);
    }
    
    FreeLibrary(hRngDll);
    return 0;
}
```

### Using Ultra Mode for Maximum Security

```c
#include <stdio.h>
#include <windows.h>

// Import the DLL function
typedef int (*MaxRNG_Ultra_Func)(unsigned char*, int, int);

int main() {
    HMODULE hRngDll = LoadLibrary("hRng.dll");
    if (!hRngDll) {
        printf("Failed to load hRng.dll\n");
        return 1;
    }
    
    MaxRNG_Ultra_Func ultraRng = 
        (MaxRNG_Ultra_Func)GetProcAddress(hRngDll, "maxrng_ultra");
    
    if (!ultraRng) {
        printf("Failed to get function address\n");
        FreeLibrary(hRngDll);
        return 1;
    }
    
    // Generate high-security random bytes (complexity level 10)
    unsigned char buffer[64] = {0};
    printf("Generating high-entropy random bytes...\n");
    
    if (ultraRng(buffer, sizeof(buffer), 10)) {
        printf("Random bytes generated successfully:\n");
        for (int i = 0; i < sizeof(buffer); i++) {
            printf("%02X ", buffer[i]);
            if ((i + 1) % 16 == 0) printf("\n");
        }
    } else {
        printf("Failed to generate random bytes\n");
    }
    
    FreeLibrary(hRngDll);
    return 0;
}
```

## Technical Details

### Entropy Sources

The library collects entropy from multiple sources:

1. **Hardware RNG (RDRAND)**
   - Uses Intel's RDRAND instruction when available
   - Implements retry logic for reliability (up to 10 retries)

2. **CPU-specific Sources**
   - RDTSC (Read Time-Stamp Counter)
   - CPUID information

3. **System Performance Metrics**
   - Process memory information via GetProcessMemoryInfo
   - High-precision performance counters via QueryPerformanceCounter

4. **Storage Information**
   - Disk free space statistics via GetDiskFreeSpaceEx

5. **Audio Timing**
   - Timing-based entropy collection with sleep intervals
   - Used as a fallback entropy source

6. **Battery/Power Information**
   - System power status via GetSystemPowerStatus

7. **Network Statistics**
   - TCP statistics via GetTcpStatistics
   - Network adapter information via GetAdaptersInfo

### Entropy Mixing

All entropy sources are securely combined using SHA-256 through the Windows BCrypt API:

- Multiple rounds of hashing based on the complexity parameter
- Secure handling of hash state between rounds
- Proper cleanup of cryptographic resources

### Thread Safety

- Uses Windows critical sections for thread synchronization
- Initialization of threading primitives via maxrng_init()
- Thread-safe API via maxrng_threadsafe()

### Security Considerations

- Multiple fallback mechanisms ensure reliability when hardware RNG is unavailable
- Complexity parameter allows for trading off performance vs. security
- Clean error handling with proper resource cleanup

## Building and Integration

### Requirements

- Windows operating system (Windows 7 or later)
- Visual Studio or compatible C compiler
- Required Windows libraries:
  - bcrypt.lib
  - winmm.lib
  - iphlpapi.lib
  - psapi.lib

### Linking with Your Application

When compiling your application, make sure to link against the required libraries:

```c
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "psapi.lib")
```

#### Dynamic Loading

```c
HMODULE hRngDll = LoadLibrary("hRng.dll");
if (hRngDll) {
    // Get function pointers using GetProcAddress
    // ...
}
```
