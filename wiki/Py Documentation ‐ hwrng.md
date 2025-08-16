# Hardware Random Number Generator (hwrng) Module

> The OSS `/dev/urandom` of Windows.

The `hwrng` module provides a Python interface to hardware-based random number generation capabilities through the `MaxRNG` class. This class wraps a native C library that accesses CPU hardware random number generation features (like Intel's RDRAND instruction) to produce high-quality random data with superior entropy compared to software-based PRNGs.

---

## Enumerations

### HashAlgorithm

Defines hash algorithms supported by MaxRNG.

```python
class HashAlgorithm(enum.IntEnum):
    SHA256 = 0
    SHA512 = 1
    SHA1 = 2
```

### ExpansionMode

Defines output expansion methods for MaxRNG.

```python
class ExpansionMode(enum.IntEnum):
    COUNTER = 0  # Counter-chained rehashing (default)
    HKDF = 1     # HKDF-Expand using HMAC
    HMAC = 2     # HMAC(PRK, counter || prev) stream
    XOF = 3      # XOF-like fallback using HMAC stream
```

### ThreadingMode

Defines threading models for MaxRNG.

```python
class ThreadingMode(enum.IntEnum):
    NONE = 0       # lock-free
    CRITSEC = 1    # use internal critical section
    USERLOCK = 2   # user callbacks
```

### SecurityMode

Defines security presets for MaxRNG.

```python
class SecurityMode(enum.IntEnum):
    FAST = 0
    BALANCED = 1
    SECURE = 2
```

### OutputMode

Defines output encoding formats for MaxRNG.

```python
class OutputMode(enum.IntEnum):
    RAW = 0
    HEX = 1
    BASE64 = 2
```

### MixingMode

Defines entropy mixing strategies for MaxRNG.

```python
class MixingMode(enum.IntEnum):
    ROUND_BASED = 0  # finalize each round then feed
    CONTINUOUS = 1   # one long-running hash, finalize once
```

## RNGConfig Structure

The `RNGConfig` class is a ctypes structure that allows full configuration of the random number generator.

```python
class RNGConfig(ctypes.Structure):
    _fields_ = [
        # Entropy source toggles
        ("use_cpu", ctypes.c_int),
        ("use_rdrand", ctypes.c_int),
        ("use_memory", ctypes.c_int),
        ("use_perf", ctypes.c_int),
        ("use_disk", ctypes.c_int),
        ("use_audio", ctypes.c_int),
        ("use_battery", ctypes.c_int),
        ("use_network", ctypes.c_int),

        # Hash and expansion
        ("hash_algo", ctypes.c_int),  # RNG_HASH_ALGO
        ("expansion", ctypes.c_int),  # RNG_EXP_MODE
        ("mixing", ctypes.c_int),     # RNG_MIX_MODE

        # Threading
        ("threading", ctypes.c_int),  # RNG_THREAD_MODE
        ("user_lock", ctypes.c_void_p),    # function pointer
        ("user_unlock", ctypes.c_void_p),  # function pointer

        # Seed injection
        ("seed", ctypes.c_void_p),     # const unsigned char*
        ("seed_len", ctypes.c_int),

        # Security preset and custom complexity
        ("sec_mode", ctypes.c_int),    # RNG_SECURITY_MODE
        ("complexity", ctypes.c_int),  # 1..10

        # Output format
        ("output_mode", ctypes.c_int),  # RNG_OUTPUT_MODE

        # Optional HKDF info/context for Expand
        ("info", ctypes.c_void_p),      # const unsigned char*
        ("info_len", ctypes.c_int)
    ]
```

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
- Sets up ctypes function prototypes and return types for type safety

## Basic Methods

### `is_available() -> bool`

Checks if the hardware random number generator is available on the current system.

**Returns:**
- `True` if hardware RNG is available
- `False` otherwise

**Example:**
```python
rng = MaxRNG()
if rng.is_available():
    print("Hardware RNG is available")
else:
    print("Hardware RNG is not available")
```

### `is_threading_available() -> bool`

Checks if the thread-safe version of the RNG is available.

**Returns:**
- `True` if thread-safe RNG is available
- `False` otherwise

**Example:**
```python
rng = MaxRNG()
if rng.is_threading_available():
    print("Thread-safe RNG is available")
else:
    print("Thread-safe RNG is not available")
```

### `init_threading() -> None`

Initializes the RNG for thread-safe operations.

**Example:**
```python
rng = MaxRNG()
rng.init_threading()  # Initialize the RNG for threads
```

> [!TIP]
> This method should be called before using thread-safe functions. It initializes internal synchronization primitives.

### `generate(size: int) -> bytes`

Generates random bytes using the standard RNG.

**Parameters:**
- `size` (int): Number of random bytes to generate

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `RuntimeError`: If the RNG operation fails

**Example:**
```python
rng = MaxRNG()
random_data = rng.generate(32)  # Generate 32 random bytes
```

### `generate_ultra(size: int, complexity: int = 5) -> bytes`

Generates random bytes with additional complexity for enhanced security.

**Parameters:**
- `size` (int): Number of random bytes to generate
- `complexity` (int): Level of additional entropy mixing (1-10, higher values provide potentially better randomness but slower performance)

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `ValueError`: If complexity is out of range
- `RuntimeError`: If the RNG operation fails

**Example:**
```python
rng = MaxRNG()
random_data = rng.generate_ultra(32, 3)  # Generate 32 random bytes with complexity level 3
```

### `generate_threadsafe(size: int, complexity: int = 2) -> bytes`

Generates random bytes using a thread-safe RNG function.

**Parameters:**
- `size` (int): Number of random bytes to generate
- `complexity` (int): Level of additional entropy mixing (1-5, higher values provide potentially better randomness but slower performance)

**Returns:**
- `bytes`: Random bytes of specified length

**Raises:**
- `ValueError`: If complexity is out of range
- `RuntimeError`: If threading is not available or the RNG operation fails

**Example:**
```python
rng = MaxRNG()
rng.init_threading()
random_data = rng.generate_threadsafe(32)  # Generate 32 random bytes in thread-safe mode
```

## Advanced Methods

### `create_config(security_mode=SecurityMode.BALANCED, ...) -> RNGConfig`

Creates a customized RNG configuration.

**Parameters:**
- `security_mode`: Overall security preset (FAST, BALANCED, SECURE)
- `hash_algo`: Hash algorithm to use (SHA256, SHA512, SHA1)
- `expansion`: Method to expand entropy (COUNTER, HKDF, HMAC, XOF)
- `output_mode`: Output format (RAW, HEX, BASE64)
- `complexity`: Complexity level (1-10), higher is more secure
- `mixing`: Entropy mixing strategy (ROUND_BASED, CONTINUOUS)
- `threading`: Thread-safety approach (NONE, CRITSEC, USERLOCK)
- `seed`: Optional seed material (bytes)
- `info`: Optional context info for HKDF (bytes)
- `sources`: List of entropy sources to enable ("cpu", "rdrand", "memory", "perf", "disk", "audio", "battery", "network")

**Returns:**
- `RNGConfig`: Configured RNG settings structure

**Example:**
```python
rng = MaxRNG()
config = rng.create_config(
    security_mode=SecurityMode.SECURE,
    hash_algo=HashAlgorithm.SHA512,
    output_mode=OutputMode.HEX,
    sources=["cpu", "rdrand", "memory"]
)
```

### `generate_custom(size: int, config=None, output_mode=None) -> Union[bytes, str]`

Generates random data with custom configuration.

**Parameters:**
- `size` (int): Number of bytes to generate (before encoding)
- `config`: RNGConfig structure or SecurityMode preset
- `output_mode`: Override output format in config (RAW, HEX, BASE64)

**Returns:**
- Random data in the requested format:
  - Raw bytes for OutputMode.RAW
  - Hex string for OutputMode.HEX
  - Base64 string for OutputMode.BASE64

**Raises:**
- `RuntimeError`: If random generation fails

**Example:**
```python
rng = MaxRNG()
# Using a security mode preset
hex_data = rng.generate_custom(32, SecurityMode.SECURE, OutputMode.HEX)

# Using a custom config
config = rng.create_config(hash_algo=HashAlgorithm.SHA512)
raw_data = rng.generate_custom(32, config)
```

## Convenience Methods

### `generate_hex(size: int, security: SecurityMode = SecurityMode.BALANCED) -> str`

Generates random data as a hex string.

**Parameters:**
- `size` (int): Number of random bytes to generate (before hex encoding)
- `security` (SecurityMode): Security preset to use

**Returns:**
- `str`: Hex-encoded random string (length will be 2*size)

**Example:**
```python
rng = MaxRNG()
hex_string = rng.generate_hex(16)  # Generate 16 random bytes as 32 hex characters
```

### `generate_base64(size: int, security: SecurityMode = SecurityMode.BALANCED) -> str`

Generates random data as a base64 string.

**Parameters:**
- `size` (int): Number of random bytes to generate (before base64 encoding)
- `security` (SecurityMode): Security preset to use

**Returns:**
- `str`: Base64-encoded random string

**Example:**
```python
rng = MaxRNG()
b64_string = rng.generate_base64(24)  # Generate 24 random bytes as base64
```

### `generate_secure(size: int) -> bytes`

Generates random data with the highest security settings.

**Parameters:**
- `size` (int): Number of random bytes to generate

**Returns:**
- `bytes`: Random bytes of specified length

**Example:**
```python
rng = MaxRNG()
secure_data = rng.generate_secure(32)  # Generate 32 random bytes with high security
```

### `generate_fast(size: int) -> bytes`

Generates random data with faster but still good settings.

**Parameters:**
- `size` (int): Number of random bytes to generate

**Returns:**
- `bytes`: Random bytes of specified length

**Example:**
```python
rng = MaxRNG()
fast_data = rng.generate_fast(32)  # Generate 32 random bytes quickly
```

### `generate_secure_hex(size: int) -> str`

Generates secure random data as a hex string.

**Parameters:**
- `size` (int): Number of random bytes to generate (before hex encoding)

**Returns:**
- `str`: Hex-encoded random string (length will be 2*size)

**Example:**
```python
rng = MaxRNG()
secure_hex = rng.generate_secure_hex(16)  # Generate 16 secure random bytes as 32 hex characters
```

### `generate_uint32() -> int`

Generates a random 32-bit unsigned integer.

**Returns:**
- `int`: Random integer between 0 and 2^32-1

**Example:**
```python
rng = MaxRNG()
random_int = rng.generate_uint32()  # Generate random 32-bit integer
```

### `generate_uint64() -> int`

Generates a random 64-bit unsigned integer.

**Returns:**
- `int`: Random integer between 0 and 2^64-1

**Example:**
```python
rng = MaxRNG()
random_long = rng.generate_uint64()  # Generate random 64-bit integer
```

### `generate_float() -> float`

Generates a random float between 0.0 and 1.0.

**Returns:**
- `float`: Random float between 0.0 and 1.0

**Example:**
```python
rng = MaxRNG()
random_float = rng.generate_float()  # Generate random float between 0.0 and 1.0
```

### `generate_range(start: int, end: int) -> int`

Generates a random integer in the specified range.

**Parameters:**
- `start` (int): Lower bound (inclusive)
- `end` (int): Upper bound (exclusive)

**Returns:**
- `int`: Random integer in the range [start, end)

**Raises:**
- `ValueError`: If end is not greater than start

**Example:**
```python
rng = MaxRNG()
dice_roll = rng.generate_range(1, 7)  # Generate number between 1 and 6
```

### `choose(items: List) -> object`

Chooses a random item from a list.

**Parameters:**
- `items` (List): List of items to choose from

**Returns:**
- Random item from the list

**Raises:**
- `ValueError`: If the list is empty

**Example:**
```python
rng = MaxRNG()
options = ["apple", "banana", "cherry", "date"]
chosen = rng.choose(options)  # Randomly select a fruit
```

### `shuffle(items: List) -> List`

Shuffles a list in-place using high-quality randomness.

**Parameters:**
- `items` (List): List to shuffle

**Returns:**
- The shuffled list (same object, modified in-place)

**Example:**
```python
rng = MaxRNG()
cards = ["A", "K", "Q", "J", "10"]
shuffled = rng.shuffle(cards)  # Shuffle the cards in-place
```

## Usage Best Practices

1. **Always check availability before use:**
   ```python
   rng = MaxRNG()
   if rng.is_available():
       ... # Proceed with RNG operations
   ```

2. **For thread-safe operations:**
   ```python
   rng = MaxRNG()
   rng.init_threading()  # Initialize the RNG for threads
   if rng.is_threading_available():
       ... # Proceed with thread-safe RNG operations
   ```

3. **Handle potential exceptions:**
   ```python
   try:
       random_data = rng.generate(32)
   except RuntimeError as e:
       ... # Handle failure
   ```

4. **Choose the appropriate method based on needs:**
   - `generate()` for standard random number generation
   - `generate_ultra()` for higher security requirements that requires multiple rounds of entropy collection
   - `generate_threadsafe()` for multithreaded applications
   - `generate_hex()` or `generate_base64()` when string output is needed
   - `generate_custom()` for full control over RNG parameters

5. **Performance considerations:**
   - `generate()` and `generate_fast()` are the fastest methods
   - `generate_ultra()` and `generate_secure()` provide enhanced security at the cost of performance
   - Consider the output format requirements (raw bytes vs hex vs base64) early in design

6. **Reuse the MaxRNG instance:**
   ```python
   # Create once, reuse multiple times
   rng = MaxRNG()
   
   # Use in multiple places without reinitializing
   data1 = rng.generate(32)
   data2 = rng.generate(64)
   ```

7. **For cryptographic applications:**
   - Use `SecurityMode.SECURE` for sensitive operations
   - Consider using `generate_ultra()` with higher complexity for critical security needs
   - When using HKDF expansion mode, provide appropriate context info for domain separation

8. **Custom configuration for specialized needs:**
   ```python
   # Create configuration for a specialized use case
   config = rng.create_config(
       security_mode=SecurityMode.SECURE,
       hash_algo=HashAlgorithm.SHA512,
       expansion=ExpansionMode.HKDF,
       output_mode=OutputMode.RAW
   )
   
   # Generate data with this configuration
   data = rng.generate_custom(1024, config)
   ```
