#include <windows.h>
#include <stdint.h>
#include <immintrin.h>   // For _rdrand32_step
#include <intrin.h>      // For __cpuid

// Optional: Check if CPU supports RDRAND instruction
int has_rdrand() {
    int info[4];
    __cpuid(info, 1); // Call CPUID with EAX=1
    return (info[2] & (1 << 30)) != 0; // Check bit 30 of ECX
}

// Fill buffer with hardware RNG bytes using RDRAND
__declspec(dllexport)
int read_hwrng(unsigned char* buffer, int size) {
    if (!has_rdrand()) {
        return 0; // CPU does not support RDRAND
    }

    int i = 0;
    uint32_t rnd;

    while (i < size) {
        if (!_rdrand32_step(&rnd)) {
            return 0; // Hardware RNG failed
        }

        for (int j = 0; j < 4 && i < size; ++j, ++i) {
            buffer[i] = (rnd >> (j * 8)) & 0xFF;
        }
    }

    return 1;
}
