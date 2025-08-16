import ctypes
from pyCTools._loadDLL import load_dll


class MaxRNG:
    """
    Python wrapper for the MaxRNG hardware random number generator DLL.

    This class dynamically loads the appropriate hRng DLL for the system architecture
    and exposes methods corresponding to the DLL's RNG functions.

    Methods:
        - test_rng_available() -> bool
            Checks if the RNG hardware is available.

        - test_threading_available() -> bool
            Checks if the thread-safe RNG is available.

        - maxrng(size: int) -> bytes
            Generates `size` bytes of random data using the standard RNG function.

        - maxrng_ultra(size: int, complexity: int) -> bytes
            Generates `size` bytes of random data with specified complexity level.

        - maxrng_threadsafe(size: int) -> bytes
            Generates `size` bytes of random data using the thread-safe RNG function.

    Raises:
        RuntimeError: If any RNG function call fails or threading is not available.
    """

    def __init__(self):
        # Load the DLL using the load_dll helper with WinDLL loader
        self.dll = load_dll(dll_prefix_name="hRng", dll_load_func=ctypes.WinDLL)

        # Define the argument and return types for DLL functions for proper ctypes binding:

        # int test_rng_available(void)
        self.dll.test_rng_available.argtypes = []
        self.dll.test_rng_available.restype = ctypes.c_int

        # int test_threading_available(void)
        self.dll.test_threading_available.argtypes = []
        self.dll.test_threading_available.restype = ctypes.c_int

        # int maxrng(unsigned char *buffer, int size)
        self.dll.maxrng.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.dll.maxrng.restype = ctypes.c_int

        # int maxrng_ultra(unsigned char *buffer, int size, int complexity)
        self.dll.maxrng_ultra.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int]
        self.dll.maxrng_ultra.restype = ctypes.c_int

        # int maxrng_threadsafe(unsigned char *buffer, int size)
        self.dll.maxrng_threadsafe.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
        self.dll.maxrng_threadsafe.restype = ctypes.c_int

    def test_rng_available(self) -> bool:
        """
        Check if the RNG hardware is available.

        Returns:
            bool: True if RNG hardware is available, False otherwise.
        """
        return self.dll.test_rng_available() == 1

    def test_threading_available(self) -> bool:
        """
        Check if thread-safe RNG functionality is available.

        Returns:
            bool: True if threading RNG is available, False otherwise.
        """
        return self.dll.test_threading_available() == 1

    def maxrng(self, size: int) -> bytes:
        """
        Generate random bytes using the standard RNG.

        Args:
            size (int): Number of random bytes to generate.

        Returns:
            bytes: Random bytes generated.

        Raises:
            RuntimeError: If the RNG function call fails.
        """
        buf = (ctypes.c_ubyte * size)()  # Allocate buffer for output
        success = self.dll.maxrng(buf, size)
        if not success:
            raise RuntimeError("maxrng failed")
        return bytes(buf)

    def maxrng_ultra(self, size: int, complexity: int) -> bytes:
        """
        Generate random bytes with a specified complexity level.

        Args:
            size (int): Number of random bytes to generate.
            complexity (int): Complexity level parameter for RNG.

        Returns:
            bytes: Random bytes generated.

        Raises:
            RuntimeError: If the RNG function call fails.
        """
        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_ultra(buf, size, complexity)
        if not success:
            raise RuntimeError("maxrng_ultra failed")
        return bytes(buf)

    def maxrng_threadsafe(self, size: int) -> bytes:
        """
        Generate random bytes using thread-safe RNG function.

        This method requires that threading is available in the RNG implementation.
        It is recommended to check availability with `test_threading_available()`
        before calling this function.

        Args:
            size (int): Number of random bytes to generate.

        Returns:
            bytes: Random bytes generated.

        Raises:
            RuntimeError: If threading is not available or the RNG call fails.
        """
        if not self.test_threading_available():
            raise RuntimeError(
                "Threading is not available in this RNG implementation.\n"
                "[?] Have you called 'MaxRNG().dll.maxrng_init()' before using 'MaxRNG().maxrng_threadsafe()'.\n"
                "[!] Best practice is to call 'MaxRNG().test_threading_available()' and only run "
                "'MaxRNG().maxrng_threadsafe()' if the returned value is True."
            )

        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_threadsafe(buf, size)
        if not success:
            raise RuntimeError("maxrng_threadsafe failed")
        return bytes(buf)

    def setup_threads(self):
        """
        Initialize the RNG for thread-safe operations.

        This method should be called before using `maxrng_threadsafe()`.
        It prepares the RNG for multithreaded access.

        Raises:
            RuntimeError: If the initialization fails.
        """
        self.dll.maxrng_init()
        if not self.test_threading_available():
            raise RuntimeError(
                "Failed to initialize RNG for threading. "
                "Ensure that the hRng DLL supports thread-safe operations."
            )
