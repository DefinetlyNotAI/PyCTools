from pyCTools.hwrng import (
    get_hardware_random_bytes,
    get_hardware_random_bytes_threadsafe,
    get_hardware_random_bytes_extended,
    hardware_rng_selftest,
)

if __name__ == '__main__':
    print("RNG self-test:", "PASS" if hardware_rng_selftest() else "FAIL")

    try:
        rb = get_hardware_random_bytes(32)
        print("MaxRNG (32 bytes):", rb.hex())
        rb2 = get_hardware_random_bytes_threadsafe(32)
        print("MaxRNG_ThreadSafe (32 bytes):", rb2.hex())
        rb3 = get_hardware_random_bytes_extended(32, intensive_level=3)
        print("MaxRNG_Extended (32 bytes, level 3):", rb3.hex())
    except Exception as e:
        print("Error:", e)
