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

# Testing MAXRNG

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
