# Hardware Random Number Generator (hwrng) Module

> The OSS `/dev/urandom` of Windows.

The `hwrng` module provides a Python interface to hardware-based random number generation capabilities through the `MaxRNG` class. This class wraps a native C library that accesses CPU hardware random number generation features (like Intel's RDRAND instruction) to produce high-quality random data with superior entropy compared to software-based PRNGs.

---

## MaxRNG Class

`MaxRNG` is a wrapper class for hardware-based random number generation that interfaces with a native DLL (`hRng_x64.dll` or `hRng_x86.dll` depending on architecture). It automatically detects the system architecture and loads the appropriate binary through the centralized `_loadDLL` module.

### Initialization
```python
rng = MaxRNG()
```

When instantiating the class, it performs the following operations:
- Loads the appropriate DLL using the `load_dll` helper function:
  - Determines system architecture (x86/x64) automatically
  - Searches for the appropriate DLL in the standard distribution paths
  - Configures the loader to use `ctypes.WinDLL` specifically for this module
- Sets up ctypes function prototypes and return types for type safety:
  - Defines appropriate argument types for all DLL functions
  - Defines appropriate return types for all DLL functions

## Methods

### `test_rng_available() -> bool`

Checks if the hardware random number generator is available on the current system.

**Returns:**
- `True` if hardware RNG is available
- `False` otherwise

**Implementation Details:**
- Calls the C function `test_rng_available()` in the DLL
- Returns `True` if the function returns `1`, `False` otherwise
- Does not throw exceptions, making it safe to use for feature detection

**Example:**
```python
rng = MaxRNG()
if rng.test_rng_available():
    print("Hardware RNG is available")
else:
    print("Hardware RNG is not available")
```

### `test_threading_available() -> bool`

Checks if the thread-safe version of the RNG is available.

**Returns:**
- `True` if thread-safe RNG is available
- `False` otherwise

**Implementation Details:**
- Calls the C function `test_threading_available()` in the DLL
- Returns `True` if the function returns `1`, `False` otherwise
- Does not throw exceptions, making it safe to use for feature detection

**Example:**
```python
rng = MaxRNG()
if rng.test_threading_available():
    print("Thread-safe RNG is available")
else:
    print("Thread-safe RNG is not available")
```

> [!TIP]
> Use this method to check if you can safely use the `maxrng_threadsafe()` method without risking threading issues.
> 
> If you ever get `False` here, check if you have initialized the threading module via `MaxRNG().dll.maxrng_init()`

### `maxrng(size: int) -> bytes`

Generates random bytes using the hardware RNG.

**Parameters:**
- `size` (int): Number of random bytes to generate

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `RuntimeError`: If the RNG operation fails

**Implementation Details:**
- Allocates a buffer of specified size using `ctypes.c_ubyte * size`
- Calls the C function `maxrng` with the buffer and size
- Checks the return value for success (non-zero)
- Converts the ctypes buffer to Python bytes before returning

**Example:**
```python
rng = MaxRNG()
random_data = rng.maxrng(32)  # Generate 32 random bytes
```

### `maxrng_ultra(size: int, complexity: int) -> bytes`

Generates random bytes with additional complexity for enhanced security.

**Parameters:**
- `size` (int): Number of random bytes to generate
- `complexity` (int): Level of additional entropy mixing (higher values provide potentially better randomness but slower performance)

> [!IMPORTANT]
> The time complexity of this method is `O(c + f)`, where `c` is complexity and `f` is amount of data flags set to be collected.

> [!TIP]
> If `complexity` is set to `1`, this method behaves like `maxrng()`. For this case, prefer using `maxrng()` for better code readability.

> [!NOTE]
> The `complexity` parameter controls the level of additional entropy mixing. Valid values are integers from `1` to `10`. Values outside this range are automatically clamped to the nearest valid value.

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `RuntimeError`: If the RNG operation fails

**Implementation Details:**
- Allocates a buffer of specified size using `ctypes.c_ubyte * size`
- Calls the C function `maxrng_ultra` with the buffer, size, and complexity level
- Checks the return value for success (non-zero)
- Converts the ctypes buffer to Python bytes before returning

**Example:**
```python
rng = MaxRNG()
random_data = rng.maxrng_ultra(32, 3)  # Generate 32 random bytes with complexity level 3
```

<details>

#### Effect of Higher `complexity` values in `collect_entropy`

- **Number of Rounds:**  
  The `complexity` parameter sets how many hashing rounds occur. Each round collects entropy from multiple sources and hashes it.

- **Entropy Collection per Round:**  
  Each round gathers entropy from:
    - Hardware RNG (RDRAND) if available
    - CPU state
    - Process memory
    - Performance counters
    - Disk activity
    - Audio input
    - Battery status
    - Network state  
      These inputs are fed into a SHA-256 hash context.

- **Hash Chaining:**  
  After each round, the resulting hash is used as input for the next round’s hash initialization. This creates a chained hash structure, improving mixing of entropy across rounds.

- **CPU and I/O Overhead:**  
  Increasing `complexity` linearly multiplies the CPU and I/O load, since all entropy sources are polled and hashed anew each round.

- **Final Output:**  
  The function outputs the final hash result after all rounds, repeating bytes if requested output size exceeds hash length (32 bytes).

- **Security Implications:**
    - More rounds increase entropy mixing, potentially enhancing unpredictability.
    - Multiple rounds help mitigate weaknesses in individual entropy sources by combining their outputs repeatedly.
    - Diminishing returns may occur if entropy sources do not provide fresh or sufficient randomness per round.

- **Failure Handling:**  
  On any cryptographic API failure, the function aborts early and returns 0, ensuring no partial or weak output is produced.

#### Summary
Higher `complexity` increases the number of entropy collection and hashing iterations, enhancing entropy mixing at the cost of greater processing time and resource usage.

</details>

### `maxrng_threadsafe(size: int) -> bytes`

Thread-safe version of the `maxrng()` function.

> [!NOTE]
> Uses the exact same algorithm as `maxrng()`, but ensures that the RNG operation is safe to call from multiple threads without risking data corruption
> 
> So yes the `complexity` parameter is `1` here.

**Parameters:**
- `size` (int): Number of random bytes to generate

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `RuntimeError`: If threading is not available or if the RNG operation fails

**Implementation Details:**
- First checks if threading is available by calling `test_threading_available()`
- If not available, raises a detailed RuntimeError with best practices advice
- Allocates a buffer of specified size using `ctypes.c_ubyte * size`
- Calls the C function `maxrng_threadsafe` with the buffer and size
- Checks the return value for success (non-zero)
- Converts the ctypes buffer to Python bytes before returning

**Example:**
```python
rng = MaxRNG()
if rng.test_threading_available():
    random_data = rng.maxrng_threadsafe(32)  # Generate 32 random bytes in thread-safe mode
```

## Error Handling

The class implements comprehensive error handling:

- **Feature Detection**: Non-throwing methods `test_rng_available()` and `test_threading_available()` for safely detecting capabilities
- **Operation Validation**: All generator methods check return values and raise descriptive exceptions
- **Threading Safety Check**: The `maxrng_threadsafe()` method validates threading availability before attempting operations - as well as providing a detailed error message if threading is not available and how to resolve it
- **Detailed Error Messages**: Clear error messages when operations fail, including best practices advice

## Memory Management

The class handles all memory allocation and deallocation for the buffer used to store random data, ensuring no memory leaks occur during operation:

- Uses properly sized ctypes buffers for each operation
- Converts C buffers to Python bytes objects which are managed by Python's garbage collector
- Ensures C memory is properly released after each operation

## Usage Best Practices

1. **Always check availability before use:**
   ```python
   rng = MaxRNG()
   if rng.test_rng_available():
       ... # Proceed with RNG operations
   ```

2. **For thread-safe operations:**
   ```python
   rng = MaxRNG()
   rng.dll.maxrng_init()  # Initialize the RNG for threads, Without this threading will always raise RuntimeError
   if rng.test_threading_available():
       ... # Proceed with thread-safe RNG operations - though this is also optional as no system hard-crash will occur (due to memory access errors), but a `raise RuntimeError` will be thrown
   ```

3. **Handle potential exceptions:**
   ```python
   try:
       random_data = rng.maxrng(32)
   except RuntimeError as e:
       ... # Handle failure
   ```

4. **Choose the appropriate method:**
   - `maxrng()` for standard random number generation
   - `maxrng_ultra()` for higher security requirements that requires multiple rounds of entropy collection
   - `maxrng_threadsafe()` for multithreaded applications that would have used `maxrng()` otherwise

5. **Performance considerations:**
   - `maxrng()` is the fastest method with basic hardware randomness (aka complexity of 1)
   - `maxrng_ultra()` provides enhanced security at the cost of performance
     - Lower complexity values in `maxrng_ultra()` offer better performance with reasonable security (1-10)

6. **Reuse the MaxRNG instance:**
   ```python
   # Create once, reuse multiple times
   rng = MaxRNG()
   
   # Use in multiple places without reinitializing thus saving performance
   data1 = rng.maxrng(32)
   data2 = rng.maxrng(64)
   ```

# Proper Examples and tests

## Example script

This is a comprehensive script that can be used to fully test `hwrng` properly

<details>
<summary>Code example</summary>

```python
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
import time
from concurrent.futures import ThreadPoolExecutor

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
            start_time_ = time.time()
            data = rng.maxrng_threadsafe(size)
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
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"\n❌ Unhandled exception: {err}")
        print("Demonstration terminated.")
```

</details>

## Testing robustness of `maxrng`

> [!NOTE]
> Do note that this code will generate a bin file called `rng_output.bin`

<details>
<summary>Code used to get the results</summary>

```python
import math
import os
import threading

from tqdm import tqdm

from pyCTools import MaxRNG


def shannon_entropy(data: bytes):
    if not data:
        return None
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    entropy = 0.0
    length = len(data)
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    print(f"Shannon Entropy:")
    print(f"    {entropy:.4f} bits per byte")
    return None


def frequency_test(data: bytes):
    zeros = sum(bin(b).count("0") for b in data)
    ones = sum(bin(b).count("1") for b in data)
    print("Frequency test:")
    print(f"    Total bits: {len(data) * 8}")
    print(f"    Zeros: {zeros}")
    print(f"    Ones: {ones}")


def runs_test(data: bytes):
    bits = ''.join(f'{b:08b}' for b in data)
    runs = 1
    prev_bit = bits[0]

    run_lengths = []
    current_run_length = 1

    for bit in bits[1:]:
        if bit == prev_bit:
            current_run_length += 1
        else:
            run_lengths.append(current_run_length)
            current_run_length = 1
            runs += 1
        prev_bit = bit
    run_lengths.append(current_run_length)

    avg_run_length = sum(run_lengths) / len(run_lengths)
    max_run_length = max(run_lengths)
    min_run_length = min(run_lengths)

    print("Runs test:")
    print(f"    Runs: {runs}")
    print(f"    Avg run length: {avg_run_length:.2f}")
    print(f"    Max run length: {max_run_length}")
    print(f"    Min run length: {min_run_length}")


def autocorrelation_test(data: bytes, lag=1):
    bits = ''.join(f'{b:08b}' for b in data)
    n = len(bits)
    matches = 0
    for i in range(n - lag):
        if bits[i] == bits[i + lag]:
            matches += 1
    autocorr = matches / (n - lag)
    print(f"Autocorrelation test (lag={lag}):")
    print(f"    Autocorrelation: {autocorr:.4f} (expected ~0.5)")


def bit_position_frequency(data: bytes):
    print("Bit position frequency test:")
    counts = [0] * 8  # count of set bits per position
    total_bytes = len(data)

    for b in data:
        for i in range(8):
            if b & (1 << i):
                counts[i] += 1

    for i, c in enumerate(counts):
        freq = c / total_bytes
        print(f"    Bit position {i}: set bit frequency = {freq:.4f} (expected ~0.5)")


def main():
    print("-" * 40)
    print("Starting RNG tests...")
    print("-" * 40 + "\n")
    filename = "rng_output.bin"
    with open(filename, "rb") as f:
        data = f.read()

    print(f"Read {len(data)} bytes from {filename}\n")

    print("-" * 40)
    shannon_entropy(data)
    print("-" * 40)
    frequency_test(data)
    print("-" * 40)
    runs_test(data)
    print("-" * 40)
    autocorrelation_test(data, lag=1)
    print("-" * 40)
    autocorrelation_test(data, lag=8)
    print("-" * 40)
    bit_position_frequency(data)
    print("-" * 40)
    print("\nAll tests completed.")


def worker(rng_, size, index, results):
    try:
        data = rng_.maxrng_threadsafe(size)
        results[index] = data
    except RuntimeError as e:
        results[index] = e


def save_random_samples(total_bytes=10_000_000, chunk_size=1024):
    bytes_generated = 0

    with open("rng_output.bin", "wb") as f, tqdm(total=total_bytes, unit="B", unit_scale=True,
                                                 desc="Saving random samples") as pbar:
        while bytes_generated < total_bytes:
            num_cores = os.cpu_count() or 1
            num_threads_ = min(num_cores, (total_bytes - bytes_generated + chunk_size - 1) // chunk_size)

            results = [None] * num_threads_
            threads_ = []
            for i_ in range(num_threads_):
                size = min(chunk_size, total_bytes - bytes_generated - i_ * chunk_size)
                t_ = threading.Thread(target=worker, args=(size, i_, results))
                threads_.append(t_)
                t_.start()
            for t_ in threads_:
                t_.join()
            for i_, result_ in enumerate(results):
                if isinstance(result_, Exception):
                    raise result_
                f.write(result_)
                bytes_generated += len(result_)
                pbar.update(len(result_))
    print(f"Saved {bytes_generated} bytes to rng_output.bin")


if __name__ == "__main__":
    # Initialize the MaxRNG instance
    rng = MaxRNG()
    rng.dll.maxrng_init()

    # Create the bin file example for sample
    save_random_samples()
    print("Random samples saved to rng_output.bin")

    # Run the tests directly
    main()
```

</details>

The results mentioned here show how strong and random maxrng is, you can test the results yourself using the above code with your own generation. The binary file that produced the below result can be found [here](https://github.com/DefinetlyNotAI/PyCTools/blob/08f2e8f31d485bce279f017f716ac260d2f5eb4e/example/rng_tests/rng_output.bin) {commit:[08f2e8f](https://github.com/DefinetlyNotAI/PyCTools/commit/08f2e8f31d485bce279f017f716ac260d2f5eb4e)}

```text
PS > python .\rng_test.py
----------------------------------------
Starting RNG tests...
----------------------------------------

Read 10000000 bytes from rng_output.bin

----------------------------------------
Shannon Entropy:
    8.0000 bits per byte
----------------------------------------
Frequency test:
    Total bits: 80000000
    Zeros: 40073282
    Ones: 40009833
----------------------------------------
Runs test:
    Runs: 40001087
    Avg run length: 2.00
    Max run length: 27
    Min run length: 1
----------------------------------------
Autocorrelation test (lag=1):
    Autocorrelation: 0.5000 (expected ~0.5)
----------------------------------------
Autocorrelation test (lag=8):
    Autocorrelation: 0.5000 (expected ~0.5)
----------------------------------------
Bit position frequency test:
    Bit position 0: set bit frequency = 0.4999 (expected ~0.5)
    Bit position 1: set bit frequency = 0.5001 (expected ~0.5)
    Bit position 2: set bit frequency = 0.5002 (expected ~0.5)
    Bit position 3: set bit frequency = 0.5002 (expected ~0.5)
    Bit position 4: set bit frequency = 0.5001 (expected ~0.5)
    Bit position 5: set bit frequency = 0.5002 (expected ~0.5)
    Bit position 6: set bit frequency = 0.5000 (expected ~0.5)
    Bit position 7: set bit frequency = 0.5002 (expected ~0.5)
----------------------------------------
```
