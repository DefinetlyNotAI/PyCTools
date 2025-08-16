"""
Comprehensive example demonstrating all features of MaxRNG from the pyCTools module.

This example shows:
1. Initializing and checking hardware RNG availability
2. Using different RNG methods (basic, ultra, thread-safe)
3. Working with different complexity levels
4. Proper multi-threading implementation
5. Error handling and best practices
6. Practical applications (encryption keys, random file generation)
7. Performance benchmarking
8. Advanced configuration options and output formats
9. Entropy source selection and customization
10. Using different hash algorithms and expansion methods
"""
import base64
import hashlib
import os
import secrets
import time
from concurrent.futures import ThreadPoolExecutor

from pyCTools.hwrng import (
    MaxRNG, HashAlgorithm, ExpansionMode, OutputMode,
    SecurityMode
)


def print_separator(title: str = None) -> None:
    """Print a separator with an optional title."""
    print("\n" + "=" * 80)
    if title:
        print(title)
        print("=" * 80)


def hex_format(data: bytes, bytes_per_line: int = 16) -> str:
    """Format bytes as a nicely formatted hex dump with ASCII representation."""
    result = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        hex_part = ' '.join(f'{b:02x}' for b in chunk)

        # Pad the hex part to align the ASCII part
        padding = '   ' * (bytes_per_line - len(chunk))

        # Create ASCII representation
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)

        result.append(f"{i:04x}:  {hex_part}{padding}  |{ascii_part}|")
    return '\n'.join(result)


def check_rng_availability() -> bool:
    """
    Check if hardware RNG is available and print detailed information.

    Returns:
        bool: True if RNG is fully available (including threading)
    """
    print_separator("HARDWARE RNG AVAILABILITY CHECK")

    try:
        rng = MaxRNG()

        # Check basic RNG availability
        rng_available = rng.is_available()
        print(f"Hardware RNG: {'AVAILABLE' if rng_available else 'NOT AVAILABLE'}")

        if not rng_available:
            print("⚠️ Hardware RNG not available. This could be because:")
            print("  - Your CPU doesn't support the RDRAND instruction")
            print("  - The RNG hardware module is disabled in BIOS/UEFI")
            print("  - The DLL failed to detect the hardware properly")
            return False

        # First check if threading is available before initialization
        pre_init_threading = rng.is_threading_available()
        print(f"Threading support before initialization: {'YES' if pre_init_threading else 'NO'}")

        # Initialize threading support
        print("\nInitializing RNG threading support...")
        try:
            rng.init_threading()
            print("✓ RNG threading initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize RNG threading: {e}")
            return False

        # Check again after initialization
        post_init_threading = rng.is_threading_available()
        print(f"Threading support after initialization: {'YES' if post_init_threading else 'NO'}")

        if post_init_threading:
            print("\n✓ Hardware RNG is FULLY AVAILABLE with threading support")
            return True
        else:
            print("\n⚠️ Hardware RNG is available but threading support failed to initialize")
            return False

    except Exception as e:
        print(f"❌ Error checking RNG availability: {e}")
        return False


def basic_rng_demo() -> None:
    """Demonstrate the basic RNG functionality."""
    print_separator("BASIC RNG DEMONSTRATION")

    rng = MaxRNG()

    # Generate different sizes of random data
    sizes = [16, 32, 64, 128, 256]

    print("Generating random bytes of different sizes using basic generate():")
    for size in sizes:
        random_bytes = rng.generate(size)
        print(f"\n{size} random bytes:")
        print(hex_format(random_bytes))
        print(f"Base64: {base64.b64encode(random_bytes).decode()}")

    print("\nThis basic RNG function is suitable for:")
    print("- General purpose random number generation")
    print("- Applications where standard randomness quality is sufficient")
    print("- Non-threaded environments")


def ultra_rng_demo() -> None:
    """Demonstrate the ultra RNG functionality with different complexity levels."""
    print_separator("ULTRA RNG DEMONSTRATION")

    rng = MaxRNG()

    # Demonstrate different complexity levels
    print("The generate_ultra() function allows specifying a 'complexity' parameter")
    print("Higher complexity values produce higher-quality randomness at the cost of performance")
    print("\nGenerating 64 bytes with different complexity levels:")

    complexities = [1, 3, 5, 7, 10]

    # Track timing for performance comparison
    timing_results = []

    for complexity in complexities:
        start_time = time.time()
        random_bytes = rng.generate_ultra(64, complexity)
        elapsed = time.time() - start_time
        timing_results.append((complexity, elapsed))

        print(f"\nComplexity level {complexity} (took {elapsed:.6f} seconds):")
        print(hex_format(random_bytes))

    print("\nPerformance comparison:")
    print("Complexity | Time (seconds) | Relative Speed")
    print("-----------+---------------+--------------")
    base_time = timing_results[0][1]  # Use complexity 1 as baseline
    for complexity, elapsed in timing_results:
        relative = elapsed / base_time
        print(f"{complexity:^11} | {elapsed:^15.6f} | {relative:^14.2f}x")

    print("\nRecommended complexity levels:")
    print("- 1-2:  Good for non-critical applications, fastest performance")
    print("- 3-6:  Good balance for cryptographic applications")
    print("- 7-10: For highest security requirements, slower performance")


def threaded_rng_demo() -> None:
    """Demonstrate thread-safe RNG functionality."""
    print_separator("THREAD-SAFE RNG DEMONSTRATION")

    rng = MaxRNG()

    # Ensure threading is available
    if not rng.is_threading_available():
        print("⚠️ Thread-safe RNG not available. Make sure init_threading() was called.")
        try:
            print("Attempting to initialize threading support now...")
            rng.init_threading()
            if rng.is_threading_available():
                print("✓ Successfully initialized threading support")
            else:
                print("❌ Failed to initialize threading support even after calling init_threading()")
                return
        except Exception as e:
            print(f"❌ Error initializing threading support: {e}")
            return

    # Single-threaded demonstration first
    print("\nSingle-threaded example:")
    random_bytes = rng.generate_threadsafe(64)
    print(hex_format(random_bytes))

    # Multithreaded demonstration
    print("\nMulti-threaded example:")

    def worker_function(thread_id, size):
        """Worker function that generates random bytes in a thread."""
        try:
            start_time_ = time.time()
            data = rng.generate_threadsafe(size)
            elapsed = time.time() - start_time_
            return {
                "thread_id": thread_id,
                "data": data,
                "size": size,
                "time": elapsed,
                "success": True
            }
        except Exception as e_:
            return {
                "thread_id": thread_id,
                "error": str(e_),
                "success": False
            }

    # Use ThreadPoolExecutor for cleaner thread management
    num_threads = 8
    bytes_per_thread = 32
    print(f"Spawning {num_threads} threads, each generating {bytes_per_thread} bytes...")

    results = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit all tasks and collect futures
        futures = [executor.submit(worker_function, i, bytes_per_thread)
                   for i in range(num_threads)]

        # Wait for all to complete and collect results
        for future in futures:
            results.append(future.result())

    # Report results
    success_count = sum(1 for r in results if r["success"])
    print(f"\n✓ {success_count}/{num_threads} threads completed successfully")

    for result in results:
        if result["success"]:
            print(f"\nThread {result['thread_id']} ({result['time']:.6f}s):")
            # Just show a portion of the data for brevity
            print(f"  {result['data'][:16].hex()}...")
        else:
            print(f"\n❌ Thread {result['thread_id']} failed: {result['error']}")

    # Higher concurrency stress test
    print("\nHigh concurrency stress test (50 threads):")
    num_stress_threads = 50
    stress_size = 16

    with ThreadPoolExecutor(max_workers=num_stress_threads) as executor:
        start_time = time.time()
        futures = [executor.submit(worker_function, i, stress_size)
                   for i in range(num_stress_threads)]

        # Wait for all to complete
        success_count = sum(1 for future in futures if future.result()["success"])
        total_time = time.time() - start_time

    print(f"✓ {success_count}/{num_stress_threads} threads completed in {total_time:.3f}s")
    print(f"Average time per thread: {total_time / num_stress_threads:.6f}s")
    print(f"Total random data generated: {success_count * stress_size} bytes")

    print("\nThe thread-safe RNG function is essential for:")
    print("- Multi-threaded applications requiring random data")
    print("- Server applications handling concurrent requests")
    print("- Parallel processing of random data")


def advanced_configuration_demo() -> None:
    """Demonstrate advanced configuration options of the MaxRNG."""
    print_separator("ADVANCED CONFIGURATION DEMONSTRATION")

    rng = MaxRNG()

    print("The MaxRNG library supports extensive configuration options")
    print("through the RNGConfig structure and generate_custom() method.\n")

    # Demonstrate different hash algorithms
    print("1. HASH ALGORITHM COMPARISON")
    print("Different hash algorithms offer different security vs. performance tradeoffs")

    hash_algos = [
        (HashAlgorithm.SHA256, "SHA-256"),
        (HashAlgorithm.SHA512, "SHA-512"),
        (HashAlgorithm.SHA1, "SHA-1 (legacy)")
    ]

    for algo, name in hash_algos:
        # Create config with specific hash algorithm
        config = rng.create_config(hash_algo=algo)

        start_time = time.time()
        data = rng.generate_custom(64, config)
        elapsed = time.time() - start_time

        print(f"\n{name} ({elapsed:.6f}s):")
        print(hex_format(data[:32]))  # Show first 32 bytes

    # Demonstrate different expansion methods
    print("\n2. ENTROPY EXPANSION METHODS")
    print("Different methods to expand limited entropy into longer outputs")

    expansion_modes = [
        (ExpansionMode.COUNTER, "Counter mode"),
        (ExpansionMode.HKDF, "HKDF expansion"),
        (ExpansionMode.HMAC, "HMAC chaining"),
        (ExpansionMode.XOF, "XOF-like expansion")
    ]

    for mode, name in expansion_modes:
        config = rng.create_config(expansion=mode)
        data = rng.generate_custom(32, config)

        print(f"\n{name}:")
        print(hex_format(data))

    # Demonstrate different output formats
    print("\n3. OUTPUT FORMAT OPTIONS")
    print("The library supports various output formats without manual conversion")

    output_sample = "Same 32 random bytes in different formats:"

    # Generate the same random data in different formats
    raw_bytes = rng.generate_custom(32, output_mode=OutputMode.RAW)
    hex_str = rng.generate_hex(32)
    base64_str = rng.generate_base64(32)

    print(f"\n{output_sample}")
    print(f"RAW:    {hex_format(raw_bytes)}")
    print(f"HEX:    {hex_str}")
    print(f"BASE64: {base64_str}")

    # Demonstrate security presets
    print("\n4. SECURITY PRESETS")
    print("Pre-configured security levels to balance security and performance")

    security_modes = [
        (SecurityMode.FAST, "Fast mode"),
        (SecurityMode.BALANCED, "Balanced mode"),
        (SecurityMode.SECURE, "Secure mode")
    ]

    for mode, name in security_modes:
        start_time = time.time()
        data = rng.generate_custom(64, mode)
        elapsed = time.time() - start_time

        print(f"\n{name} ({elapsed:.6f}s):")
        print(hex_format(data[:32]))  # Show first 32 bytes


def entropy_sources_demo() -> None:
    """Demonstrate selection of entropy sources."""
    print_separator("ENTROPY SOURCES DEMONSTRATION")

    rng = MaxRNG()

    print("The MaxRNG library can use multiple entropy sources")
    print("Each source provides different types of randomness\n")

    # All available sources
    all_sources = ["cpu", "rdrand", "memory", "perf", "disk", "audio", "battery", "network"]

    # Test each source individually
    print("INDIVIDUAL ENTROPY SOURCES:")

    for source in all_sources:
        try:
            config = rng.create_config(sources=[source])
            data = rng.generate_custom(16, config)

            print(f"\n{source.upper()} source only:")
            print(hex_format(data))
        except Exception as e:
            print(f"\n{source.upper()} source failed: {e}")

    # Combine sources for better entropy
    print("\nCOMBINING MULTIPLE SOURCES:")

    source_groups = [
        (["cpu", "rdrand"], "CPU + RDRAND (hardware sources)"),
        (["memory", "perf"], "Memory + Performance (system sources)"),
        (["disk", "audio", "network"], "I/O sources"),
        (all_sources, "ALL sources")
    ]

    for sources, name in source_groups:
        try:
            config = rng.create_config(sources=sources)
            data = rng.generate_custom(32, config)

            print(f"\n{name}:")
            print(hex_format(data))
        except Exception as e:
            print(f"\n{name} failed: {e}")

    # Measure source performance
    print("\nSOURCE PERFORMANCE COMPARISON:")
    print("Source Group | Time (seconds) | Relative Speed")
    print("-------------+----------------+--------------")

    perf_results = []
    base_time = None

    for sources, name in source_groups:
        try:
            config = rng.create_config(sources=sources)

            start_time = time.time()
            rng.generate_custom(256, config)
            elapsed = time.time() - start_time

            perf_results.append((name, elapsed))
            if base_time is None:
                base_time = elapsed

        except Exception:
            perf_results.append((name, None))

    for name, elapsed in perf_results:
        if elapsed is not None:
            relative = elapsed / base_time
            print(f"{name[:12]:13} | {elapsed:^16.6f} | {relative:^14.2f}x")
        else:
            print(f"{name[:12]:13} | {'FAILED':^16} | {'N/A':^14}")


def utility_functions_demo() -> None:
    """Demonstrate the utility functions in MaxRNG."""
    print_separator("UTILITY FUNCTIONS DEMONSTRATION")

    rng = MaxRNG()

    print("MaxRNG provides utility functions for common random number needs")

    # 1. Integer generation
    print("\n1. RANDOM INTEGER GENERATION")

    print("32-bit unsigned integers:")
    for _ in range(5):
        print(f"  {rng.generate_uint32():10d}")

    print("\n64-bit unsigned integers:")
    for _ in range(5):
        print(f"  {rng.generate_uint64():20d}")

    # 2. Floating-point numbers
    print("\n2. RANDOM FLOATING-POINT NUMBERS")

    print("Random floats between 0.0 and 1.0:")
    for _ in range(5):
        print(f"  {rng.generate_float():.16f}")

    # 3. Range generation
    print("\n3. RANDOM INTEGERS IN RANGES")

    ranges = [(1, 6), (1, 100), (1000, 10000), (-50, 50)]

    for start, end in ranges:
        print(f"\nRange [{start}, {end}):")
        for _ in range(5):
            print(f"  {rng.generate_range(start, end)}")

    # 4. List operations
    print("\n4. LIST OPERATIONS")

    # Random choice
    fruits = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
    print("\nRandom choices from a list:")
    for _ in range(5):
        print(f"  {rng.choose(fruits)}")

    # List shuffling
    print("\nList shuffling:")
    for _ in range(3):
        # Make a copy to shuffle
        fruits_copy = fruits.copy()
        shuffled = rng.shuffle(fruits_copy)
        print(f"  {shuffled}")


def practical_applications() -> None:
    """Demonstrate practical applications of hardware RNG."""
    print_separator("PRACTICAL APPLICATIONS")

    rng = MaxRNG()

    # 1. Cryptographic keys
    print("\n1. GENERATING CRYPTOGRAPHIC KEYS")
    print("Hardware RNG is ideal for generating high-quality cryptographic keys")

    # AES-256 key (32 bytes)
    aes_key = rng.generate_secure(32)
    print(f"\nAES-256 Key: {aes_key.hex()}")

    # Ed25519 private key (32 bytes)
    ed25519_seed = rng.generate_secure(32)
    print(f"Ed25519 Seed: {ed25519_seed.hex()}")

    # 2. Random passwords
    print("\n2. GENERATING SECURE PASSWORDS")

    def generate_password(length=16):
        """Generate a random password using hardware RNG."""
        # Get random bytes and convert to base64
        random_bytes = rng.generate(length)
        # Use base64 encoding to get printable chars, remove padding
        b64_string = base64.b64encode(random_bytes).decode('ascii').rstrip('=')
        # Take the first 'length' characters
        return b64_string[:length]

    passwords = [generate_password(length) for length in [8, 12, 16, 24]]
    for i, password in enumerate(passwords):
        print(f"Password {i + 1} (length {len(password)}): {password}")

    # 3. Random file generation
    print("\n3. GENERATING A RANDOM FILE")

    file_size = 1024  # 1 KB
    file_path = "random_data.bin"

    with open(file_path, "wb") as f:
        # Generate data in chunks for efficiency
        chunk_size = 256
        remaining = file_size

        while remaining > 0:
            size = min(chunk_size, remaining)
            data = rng.generate(size)
            f.write(data)
            remaining -= size

    print(f"Generated random file: {file_path} ({file_size} bytes)")

    # Calculate file hash to verify randomness
    with open(file_path, "rb") as f:
        file_data = f.read()
        file_hash = hashlib.sha256(file_data).hexdigest()

    print(f"File SHA-256: {file_hash}")

    # 4. Compare with software RNG
    print("\n4. COMPARISON WITH SOFTWARE RNG")
    print("Hardware RNG vs Python's cryptographic RNG (secrets module)")

    sizes_to_test = [16, 64, 256, 1024]

    print("\nSize (bytes) | Hardware RNG time | Software RNG time | Ratio")
    print("-------------+-------------------+-------------------+-------")

    for size in sizes_to_test:
        # Hardware RNG timing
        hw_start = time.time()
        _ = rng.generate(size)
        hw_time = time.time() - hw_start

        # Software RNG timing
        sw_start = time.time()
        _ = secrets.token_bytes(size)
        sw_time = time.time() - sw_start

        # Calculate ratio (higher means hardware is slower)
        ratio = hw_time / sw_time if sw_time > 0 else float('inf')

        print(f"{size:^13} | {hw_time:^19.6f} | {sw_time:^19.6f} | {ratio:^7.2f}x")

    print("\nNote: Hardware RNG may be slower but provides pseudo-true randomness,")
    print("which is crucial for security-sensitive applications.")

    # 5. Custom seed injection
    print("\n5. CUSTOM SEED INJECTION")
    print("Using custom seed material to initialize the RNG state")

    # Create a config with custom seed
    custom_seed = b"This is a custom seed string for testing purposes!"

    # Generate different random sequences with the same seed
    config = rng.create_config(seed=custom_seed)

    print("\nRandom data with custom seed:")
    for i in range(3):
        # Each call should produce different outputs even with the same seed
        # because the internal state evolves with each use
        data = rng.generate_custom(32, config)
        print(f"Sequence {i+1}: {data[:16].hex()}...")


def error_handling_demo() -> None:
    """Demonstrate proper error handling with MaxRNG."""
    print_separator("ERROR HANDLING DEMONSTRATION")

    rng = MaxRNG()

    # 1. Invalid size parameter
    print("\n1. HANDLING INVALID SIZE PARAMETER")
    try:
        print("Attempting to generate -10 random bytes...")
        random_bytes = rng.generate(-10)
        print("Result:", random_bytes.hex())
    except Exception as e:
        print(f"✓ Caught expected error: {e}")

    # 2. Invalid complexity parameter
    print("\n2. HANDLING INVALID COMPLEXITY PARAMETER")
    try:
        print("Attempting to use complexity=15 (outside 1-10 range)...")
        random_bytes = rng.generate_ultra(32, 15)
        print("Result:", random_bytes.hex())
    except ValueError as e:
        print(f"✓ Caught expected error: {e}")

    print("\nBest practices for error handling:")
    print("1. Always check hardware availability with is_available()")
    print("2. Always initialize threading with init_threading() before threaded usage")
    print("3. Verify threading availability with is_threading_available()")
    print("4. Use try/except blocks around RNG calls in production code")
    print("5. Have a fallback mechanism for when hardware RNG is unavailable")


def main() -> None:
    """Main function to run all demonstrations."""
    print_separator("HARDWARE RANDOM NUMBER GENERATOR (HRNG) COMPREHENSIVE DEMO")
    print("This example demonstrates all features of the MaxRNG hardware RNG module")

    # First check if hardware RNG is available at all
    if not check_rng_availability():
        print("\n❌ Hardware RNG is not fully available.")
        print("Some demonstrations may fail or fall back to software RNG.")
        print("Do you want to continue anyway? (y/n)")
        if input().lower() != 'y':
            print("Exiting demonstration.")
            return

    # Show menu for demonstrations
    demos = {
        "1": ("Basic RNG Functions", basic_rng_demo),
        "2": ("Ultra RNG with Complexity Levels", ultra_rng_demo),
        "3": ("Thread-safe RNG Operations", threaded_rng_demo),
        "4": ("Advanced Configuration Options", advanced_configuration_demo),
        "5": ("Entropy Source Selection", entropy_sources_demo),
        "6": ("Utility Functions", utility_functions_demo),
        "7": ("Practical Applications", practical_applications),
        "8": ("Error Handling", error_handling_demo),
        "9": ("Run All Demos", None)
    }

    print("\nAvailable demonstrations:")
    for key, (name, _) in demos.items():
        print(f"{key}. {name}")

    choice = input("\nEnter your choice (or 'q' to quit): ").strip()

    if choice.lower() == 'q':
        print("Exiting demonstration.")
        return

    if choice == "9":
        # Run all demos
        for key, (_, func) in demos.items():
            if key != "9" and func is not None:
                func()
    elif choice in demos:
        # Run selected demo
        _, func = demos[choice]
        if func is not None:
            func()
    else:
        print("Invalid choice. Exiting.")
        return

    print_separator("DEMONSTRATION COMPLETE")

    # Clean up the random file we created
    try:
        if os.path.exists("random_data.bin"):
            os.remove("random_data.bin")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\n❌ Unhandled exception: {err}")
        print("Demonstration terminated.")
