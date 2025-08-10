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
"""
import base64
import hashlib
import os
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# Add the parent directory to sys.path to import pyCTools
# This is necessary for local testing, but once pyCTools becomes a package, this can be removed.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pyCTools import MaxRNG


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

        # Check basic RNG availability (RDRAND instruction)
        rdrand_available = rng.test_rng_available()
        print(f"RDRAND hardware instruction: {'AVAILABLE' if rdrand_available else 'NOT AVAILABLE'}")

        if not rdrand_available:
            print("⚠️ Hardware RNG not available. This could be because:")
            print("  - Your CPU doesn't support the RDRAND instruction")
            print("  - The RNG hardware module is disabled in BIOS/UEFI")
            print("  - The DLL failed to detect the hardware properly")
            return False

        # First check if threading is available before initialization
        pre_init_threading = rng.test_threading_available()
        print(f"Threading support before initialization: {'YES' if pre_init_threading else 'NO'}")

        # Initialize threading support
        print("\nInitializing RNG threading support...")
        try:
            rng.dll.maxrng_init()
            print("✓ RNG threading initialized successfully")
        except Exception as e:
            print(f"⚠️ Failed to initialize RNG threading: {e}")
            return False

        # Check again after initialization
        post_init_threading = rng.test_threading_available()
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

    print("Generating random bytes of different sizes using basic maxrng():")
    for size in sizes:
        random_bytes = rng.maxrng(size)
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
    print("The maxrng_ultra() function allows specifying a 'complexity' parameter")
    print("Higher complexity values produce higher-quality randomness at the cost of performance")
    print("\nGenerating 64 bytes with different complexity levels:")

    complexities = [1, 3, 5, 7, 10]

    # Track timing for performance comparison
    timing_results = []

    for complexity in complexities:
        start_time = time.time()
        random_bytes = rng.maxrng_ultra(64, complexity)
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
    if not rng.test_threading_available():
        print("⚠️ Thread-safe RNG not available. Make sure maxrng_init() was called.")
        try:
            print("Attempting to initialize threading support now...")
            rng.dll.maxrng_init()
            if rng.test_threading_available():
                print("✓ Successfully initialized threading support")
            else:
                print("❌ Failed to initialize threading support even after calling maxrng_init()")
                return
        except Exception as e:
            print(f"❌ Error initializing threading support: {e}")
            return

    # Single-threaded demonstration first
    print("\nSingle-threaded example:")
    random_bytes = rng.maxrng_threadsafe(64)
    print(hex_format(random_bytes))

    # Multithreaded demonstration
    print("\nMulti-threaded example:")

    def worker_function(thread_id, size):
        """Worker function that generates random bytes in a thread."""
        try:
            start_time = time.time()
            data = rng.maxrng_threadsafe(size)
            elapsed = time.time() - start_time
            return {
                "thread_id": thread_id,
                "data": data,
                "size": size,
                "time": elapsed,
                "success": True
            }
        except Exception as e:
            return {
                "thread_id": thread_id,
                "error": str(e),
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


def practical_applications() -> None:
    """Demonstrate practical applications of hardware RNG."""
    print_separator("PRACTICAL APPLICATIONS")

    rng = MaxRNG()

    # 1. Cryptographic keys
    print("\n1. GENERATING CRYPTOGRAPHIC KEYS")
    print("Hardware RNG is ideal for generating high-quality cryptographic keys")

    # AES-256 key (32 bytes)
    aes_key = rng.maxrng_ultra(32, 10)
    print(f"\nAES-256 Key: {aes_key.hex()}")

    # Ed25519 private key (32 bytes)
    ed25519_seed = rng.maxrng_ultra(32, 10)
    print(f"Ed25519 Seed: {ed25519_seed.hex()}")

    # 2. Random passwords
    print("\n2. GENERATING SECURE PASSWORDS")

    def generate_password(length=16):
        """Generate a random password using hardware RNG."""
        # Get random bytes and convert to base64
        random_bytes = rng.maxrng(length)
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
            data = rng.maxrng(size)
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
        _ = rng.maxrng(size)
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


def error_handling_demo() -> None:
    """Demonstrate proper error handling with MaxRNG."""
    print_separator("ERROR HANDLING DEMONSTRATION")

    rng = MaxRNG()

    # 1. Invalid size parameter
    print("\n1. HANDLING INVALID SIZE PARAMETER")
    try:
        print("Attempting to generate -10 random bytes...")
        random_bytes = rng.maxrng(-10)
        print("Result:", random_bytes.hex())
    except Exception as e:
        print(f"✓ Caught expected error: {e}")

    # 2. Invalid complexity parameter
    print("\n2. HANDLING INVALID COMPLEXITY PARAMETER")
    print("Attempting to use negative complexity...")
    random_bytes = rng.maxrng_ultra(32, -5)
    print("Result:", random_bytes.hex())
    print("✓ Function returned data even with invalid complexity, as it clamps to nearest valid value")

    # 3. Thread-safety without initialization
    print("\n3. HANDLING THREAD-SAFETY WITHOUT INITIALIZATION")

    print("\nBest practices for error handling:")
    print("1. Always check hardware availability with test_rng_available()")
    print("2. Always initialize threading with maxrng_init() before threaded usage")
    print("3. Verify threading availability with test_threading_available()")
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

    # Run all demonstrations
    basic_rng_demo()
    ultra_rng_demo()
    threaded_rng_demo()
    practical_applications()
    error_handling_demo()

    print_separator("DEMONSTRATION COMPLETE")

    # Clean up the random file we created
    try:
        if os.path.exists("random_data.bin"):
            os.remove("random_data.bin")
    except:
        pass


if __name__ == "__main__":
    try:
        import ctypes  # Import here for the error handling demo

        main()
    except Exception as e:
        print(f"\n❌ Unhandled exception: {e}")
        print("Demonstration terminated.")
