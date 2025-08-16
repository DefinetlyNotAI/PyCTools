import ctypes
import enum
from typing import List, Optional, Union

from pyCTools._loadDLL import load_dll


class HashAlgorithm(enum.IntEnum):
    """Hash algorithms supported by MaxRNG."""
    SHA256 = 0
    SHA512 = 1
    SHA1 = 2


class ExpansionMode(enum.IntEnum):
    """Output expansion modes for MaxRNG."""
    COUNTER = 0  # Counter-chained rehashing (default)
    HKDF = 1  # HKDF-Expand using HMAC
    HMAC = 2  # HMAC(PRK, counter || prev) stream
    XOF = 3  # XOF-like fallback using HMAC stream


class ThreadingMode(enum.IntEnum):
    """Threading modes for MaxRNG."""
    NONE = 0  # lock-free
    CRITSEC = 1  # use internal critical section
    USERLOCK = 2  # user callbacks


class SecurityMode(enum.IntEnum):
    """Security presets for MaxRNG."""
    FAST = 0
    BALANCED = 1
    SECURE = 2


class OutputMode(enum.IntEnum):
    """Output encoding formats for MaxRNG."""
    RAW = 0
    HEX = 1
    BASE64 = 2


class MixingMode(enum.IntEnum):
    """Entropy mixing strategies for MaxRNG."""
    ROUND_BASED = 0  # finalize each round then feed
    CONTINUOUS = 1  # one long-running hash, finalize once


class RNGConfig(ctypes.Structure):
    """Configuration structure for advanced MaxRNG operations."""
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
        ("mixing", ctypes.c_int),  # RNG_MIX_MODE

        # Threading
        ("threading", ctypes.c_int),  # RNG_THREAD_MODE
        ("user_lock", ctypes.c_void_p),  # function pointer
        ("user_unlock", ctypes.c_void_p),  # function pointer

        # Seed injection
        ("seed", ctypes.c_void_p),  # const unsigned char*
        ("seed_len", ctypes.c_int),

        # Security preset and custom complexity
        ("sec_mode", ctypes.c_int),  # RNG_SECURITY_MODE
        ("complexity", ctypes.c_int),  # 1..10

        # Output format
        ("output_mode", ctypes.c_int),  # RNG_OUTPUT_MODE

        # Optional HKDF info/context for Expand
        ("info", ctypes.c_void_p),  # const unsigned char*
        ("info_len", ctypes.c_int)
    ]


class MaxRNG:
    """
    Advanced wrapper for the hRng hardware random number generator.

    This class provides access to all features of the hRng library:
    - Multiple entropy sources (CPU, RDRAND, memory, performance counters, disk, audio, battery, network)
    - Various hash algorithms (SHA-256, SHA-512, SHA-1)
    - Different expansion techniques (Counter, HKDF, HMAC, XOF)
    - Thread-safety options
    - Security level presets
    - Customizable complexity
    - Multiple output formats (raw bytes, hex, base64)

    Basic usage:
        rng = MaxRNG()
        random_bytes = rng.generate(32)  # Generate 32 random bytes

    Advanced usage:
        rng = MaxRNG()
        config = rng.create_config(
            security_mode=SecurityMode.SECURE,
            hash_algo=HashAlgorithm.SHA512,
            output_mode=OutputMode.HEX
        )
        random_hex = rng.generate_custom(32, config)
    """

    # Internal handlers
    def __init__(self):
        """Initialize the MaxRNG wrapper by loading the appropriate DLL."""
        # Load the DLL using the load_dll helper with WinDLL loader
        self.dll = load_dll(dll_prefix_name="hRng", dll_load_func=ctypes.WinDLL)

        # Define basic function signatures
        self._setup_basic_functions()

        # Define advanced function signatures
        self._setup_advanced_functions()

    def _setup_basic_functions(self):
        """Set up ctypes bindings for the basic RNG functions."""
        # int test_rng_available(void)
        self.dll.test_rng_available.argtypes = []
        self.dll.test_rng_available.restype = ctypes.c_int

        # int test_threading_available(void)
        self.dll.test_threading_available.argtypes = []
        self.dll.test_threading_available.restype = ctypes.c_int

        # void maxrng_init(void)
        self.dll.maxrng_init.argtypes = []
        self.dll.maxrng_init.restype = None

        # int maxrng(unsigned char *buffer, int size)
        self.dll.maxrng.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.dll.maxrng.restype = ctypes.c_int

        # int maxrng_ultra(unsigned char *buffer, int size, int complexity)
        self.dll.maxrng_ultra.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int]
        self.dll.maxrng_ultra.restype = ctypes.c_int

        # int maxrng_threadsafe(unsigned char *buffer, int size, int complexity)
        self.dll.maxrng_threadsafe.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int]
        self.dll.maxrng_threadsafe.restype = ctypes.c_int

    def _setup_advanced_functions(self):
        """Set up ctypes bindings for the advanced RNG functions."""
        # void maxrng_dev_default_config(RNG_CONFIG *cfg, RNG_SECURITY_MODE mode)
        self.dll.maxrng_dev_default_config.argtypes = [ctypes.POINTER(RNGConfig), ctypes.c_int]
        self.dll.maxrng_dev_default_config.restype = None

        # int maxrng_dev(unsigned char *out_buf, int out_buf_len, int raw_len, const RNG_CONFIG *cfg_in)
        self.dll.maxrng_dev.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte),  # out_buf
            ctypes.c_int,  # out_buf_len
            ctypes.c_int,  # raw_len
            ctypes.POINTER(RNGConfig)  # cfg_in
        ]
        self.dll.maxrng_dev.restype = ctypes.c_int

    # Availability checks
    def is_available(self) -> bool:
        """
        Check if the RNG hardware is available.

        Returns:
            bool: True if RNG hardware is available, False otherwise.
        """
        return self.dll.test_rng_available() == 1

    def is_threading_available(self) -> bool:
        """
        Check if thread-safe RNG functionality is available.

        Returns:
            bool: True if threading RNG is available, False otherwise.
        """
        return self.dll.test_threading_available() == 1

    # Initialization methods
    def init_threading(self) -> None:
        """
        Initialize the RNG for thread-safe operations.

        This method should be called before using thread-safe functions.
        It initializes internal synchronization primitives.
        """
        self.dll.maxrng_init()

    def create_config(self,
                      security_mode: SecurityMode = SecurityMode.BALANCED,
                      hash_algo: HashAlgorithm = HashAlgorithm.SHA256,
                      expansion: ExpansionMode = ExpansionMode.COUNTER,
                      output_mode: OutputMode = OutputMode.RAW,
                      complexity: int = 2,
                      mixing: MixingMode = MixingMode.CONTINUOUS,
                      threading: ThreadingMode = ThreadingMode.NONE,
                      seed: Optional[bytes] = None,
                      info: Optional[bytes] = None,
                      sources: Optional[List[str]] = None) -> RNGConfig:
        """
        Create a customized RNG configuration.

        Args:
            security_mode: Overall security preset (FAST, BALANCED, SECURE)
            hash_algo: Hash algorithm to use (SHA256, SHA512, SHA1)
            expansion: Method to expand entropy (COUNTER, HKDF, HMAC, XOF)
            output_mode: Output format (RAW, HEX, BASE64)
            complexity: Complexity level (1-10), higher is more secure
            mixing: Entropy mixing strategy (ROUND_BASED, CONTINUOUS)
            threading: Thread-safety approach (NONE, CRITSEC, USERLOCK)
            seed: Optional seed material (bytes)
            info: Optional context info for HKDF (bytes)
            sources: List of entropy sources to enable ("cpu", "rdrand", "memory",
                    "perf", "disk", "audio", "battery", "network")

        Returns:
            RNGConfig: Configured RNG settings structure
        """
        # Create config and set defaults
        config = RNGConfig()
        self.dll.maxrng_dev_default_config(ctypes.byref(config), security_mode)

        # Apply custom settings
        config.hash_algo = hash_algo
        config.expansion = expansion
        config.output_mode = output_mode
        config.complexity = complexity
        config.mixing = mixing
        config.threading = threading

        # Set up seed if provided
        if seed:
            seed_buffer = ctypes.create_string_buffer(seed)
            config.seed = ctypes.cast(seed_buffer, ctypes.c_void_p)
            config.seed_len = len(seed)

        # Set up info for HKDF if provided
        if info:
            info_buffer = ctypes.create_string_buffer(info)
            config.info = ctypes.cast(info_buffer, ctypes.c_void_p)
            config.info_len = len(info)

        # Configure entropy sources if specified
        if sources:
            # First disable all
            config.use_cpu = config.use_rdrand = config.use_memory = config.use_perf = 0
            config.use_disk = config.use_audio = config.use_battery = config.use_network = 0

            # Then enable only requested ones
            for source in sources:
                if source.lower() == "cpu":
                    config.use_cpu = 1
                elif source.lower() == "rdrand":
                    config.use_rdrand = 1
                elif source.lower() == "memory":
                    config.use_memory = 1
                elif source.lower() == "perf":
                    config.use_perf = 1
                elif source.lower() == "disk":
                    config.use_disk = 1
                elif source.lower() == "audio":
                    config.use_audio = 1
                elif source.lower() == "battery":
                    config.use_battery = 1
                elif source.lower() == "network":
                    config.use_network = 1

        return config

    # All RNG generation methods
    def generate(self, size: int) -> bytes:
        """
        Generate random bytes using the standard RNG.

        Args:
            size (int): Number of random bytes to generate.

        Returns:
            bytes: Random bytes generated.

        Raises:
            RuntimeError: If the RNG function call fails.
        """
        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng(buf, size)
        if not success:
            raise RuntimeError("Failed to generate random data")
        return bytes(buf)

    def generate_ultra(self, size: int, complexity: int = 5) -> bytes:
        """
        Generate high-quality random bytes with specified complexity.

        Args:
            size (int): Number of random bytes to generate.
            complexity (int): Complexity level (1-10), higher is more secure.

        Returns:
            bytes: Random bytes generated.

        Raises:
            ValueError: If complexity is out of range.
            RuntimeError: If the RNG function call fails.
        """
        if not 1 <= complexity <= 10:
            raise ValueError("Complexity must be between 1 and 10")

        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_ultra(buf, size, complexity)
        if not success:
            raise RuntimeError("Failed to generate ultra random data")
        return bytes(buf)

    def generate_threadsafe(self, size: int, complexity: int = 2) -> bytes:
        """
        Generate random bytes using thread-safe RNG function.

        Args:
            size (int): Number of random bytes to generate.
            complexity (int): Complexity level (1-5), higher is more secure.

        Returns:
            bytes: Random bytes generated.

        Raises:
            ValueError: If complexity is out of range.
            RuntimeError: If threading is not available or the RNG call fails.
        """
        if not 1 <= complexity <= 5:
            raise ValueError("Complexity for thread-safe RNG must be between 1 and 5")

        if not self.is_threading_available():
            self.init_threading()
            if not self.is_threading_available():
                raise RuntimeError(
                    "Threading initialization failed. Ensure the hRng DLL supports thread-safe operations."
                )

        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_threadsafe(buf, size, complexity)
        if not success:
            raise RuntimeError("Failed to generate thread-safe random data")
        return bytes(buf)

    def generate_custom(self,
                        size: int,
                        config: Optional[Union[RNGConfig, SecurityMode]] = None,
                        output_mode: Optional[OutputMode] = None) -> Union[bytes, str]:
        """
        Generate random data with custom configuration.

        Args:
            size (int): Number of bytes to generate (before encoding)
            config: RNGConfig structure or SecurityMode preset
            output_mode: Override output format in config (RAW, HEX, BASE64)

        Returns:
            Union[bytes, str]: Random data in the requested format
                - Raw bytes for OutputMode.RAW
                - Hex string for OutputMode.HEX
                - Base64 string for OutputMode.BASE64

        Raises:
            RuntimeError: If random generation fails
        """
        # Handle the case where config is a SecurityMode enum
        if isinstance(config, SecurityMode) or config is None:
            security_mode = config if config is not None else SecurityMode.BALANCED
            config = self.create_config(security_mode=security_mode)

        # Override output mode if specified
        if output_mode is not None:
            config.output_mode = output_mode

        # Calculate needed buffer size based on output mode
        out_size = size
        if config.output_mode == OutputMode.HEX:
            out_size = size * 2
        elif config.output_mode == OutputMode.BASE64:
            # Base64 encoding: 4 * ceil(n/3)
            out_size = 4 * ((size + 2) // 3)

        # Allocate output buffer
        out_buf = (ctypes.c_ubyte * out_size)()

        # Call the advanced RNG function
        bytes_written = self.dll.maxrng_dev(
            out_buf,
            out_size,
            size,
            ctypes.byref(config)
        )

        if bytes_written <= 0:
            raise RuntimeError("Failed to generate custom random data")

        # Convert to the appropriate return type
        result = bytes(out_buf[:bytes_written])
        if config.output_mode == OutputMode.RAW:
            return result
        else:
            # For HEX and BASE64, return as string
            return result.decode('ascii')

    # Convenience methods for common random use cases
    def generate_hex(self, size: int, security: SecurityMode = SecurityMode.BALANCED) -> str:
        """Generate random data as a hex string."""
        return self.generate_custom(size, security, OutputMode.HEX)

    def generate_base64(self, size: int, security: SecurityMode = SecurityMode.BALANCED) -> str:
        """Generate random data as a base64 string."""
        return self.generate_custom(size, security, OutputMode.BASE64)

    def generate_secure(self, size: int) -> bytes:
        """Generate random data with the highest security settings."""
        return self.generate_custom(size, SecurityMode.SECURE)

    def generate_fast(self, size: int) -> bytes:
        """Generate random data with faster but still good settings."""
        return self.generate_custom(size, SecurityMode.FAST)

    def generate_secure_hex(self, size: int) -> str:
        """Generate secure random data as a hex string."""
        return self.generate_custom(size, SecurityMode.SECURE, OutputMode.HEX)

    def generate_uint32(self) -> int:
        """Generate a random 32-bit unsigned integer."""
        buf = self.generate(4)
        return int.from_bytes(buf, byteorder='little', signed=False)

    def generate_uint64(self) -> int:
        """Generate a random 64-bit unsigned integer."""
        buf = self.generate(8)
        return int.from_bytes(buf, byteorder='little', signed=False)

    def generate_float(self) -> float:
        """Generate a random float between 0.0 and 1.0."""
        # Use 4 bytes for good distribution
        value = self.generate_uint32()
        return value / (2 ** 32)

    def generate_range(self, start: int, end: int) -> int:
        """
        Generate a random integer in the specified range [start, end).

        Args:
            start: Lower bound (inclusive)
            end: Upper bound (exclusive)

        Returns:
            int: Random integer in the range
        """
        if end <= start:
            raise ValueError("End must be greater than start")

        range_size = end - start

        # Determine how many bytes we need
        if range_size <= 256:
            bytes_needed = 1
        elif range_size <= 65536:
            bytes_needed = 2
        elif range_size <= 16777216:
            bytes_needed = 3
        else:
            bytes_needed = 4

        # For large ranges, use 8 bytes
        if range_size > 4294967296:
            bytes_needed = 8

        # Get random bytes and convert to integer
        buf = self.generate(bytes_needed)
        value = int.from_bytes(buf, byteorder='little', signed=False)

        # Map to the desired range
        return start + (value % range_size)

    # Convenience methods for common operations
    def choose(self, items: List) -> object:
        """
        Choose a random item from a list.

        Args:
            items: List of items to choose from

        Returns:
            object: Randomly selected item
        """
        if not items:
            raise ValueError("List must not be empty")

        idx = self.generate_range(0, len(items))
        return items[idx]

    def shuffle(self, items: List) -> List:
        """
        Shuffle a list in-place using high-quality randomness.

        Args:
            items: List to shuffle

        Returns:
            List: The shuffled list (same object, modified in-place)
        """
        n = len(items)
        for i in range(n - 1, 0, -1):
            j = self.generate_range(0, i + 1)
            items[i], items[j] = items[j], items[i]
        return items
