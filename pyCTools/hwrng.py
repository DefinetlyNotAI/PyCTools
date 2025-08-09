import ctypes
import os
import platform


class MaxRNG:
    @staticmethod
    def _load_rng_functions():
        arch = 'x64' if platform.architecture()[0] == '64bit' else 'x86'
        dll_name = f'hRng_{arch}.dll'
        base_dir = os.path.dirname(__file__)
        possible_dist_paths = [
            os.path.join(base_dir, 'dist', arch, dll_name),
            os.path.join(base_dir, '..', 'dist', arch, dll_name),
            os.path.join(base_dir, '..', '..', 'dist', arch, dll_name),
        ]
        dll_path = None
        for path in possible_dist_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                dll_path = abs_path
                break

        if dll_path is None:
            dll_path = os.path.abspath(possible_dist_paths[0])  # fallback for error message

        return ctypes.WinDLL(dll_path)

    def __init__(self):
        self.dll = self._load_rng_functions()

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
        return self.dll.test_rng_available() == 1

    def test_threading_available(self) -> bool:
        return self.dll.test_threading_available() == 1

    def maxrng(self, size: int) -> bytes:
        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng(buf, size)
        if not success:
            raise RuntimeError("maxrng failed")
        return bytes(buf)

    def maxrng_ultra(self, size: int, complexity: int) -> bytes:
        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_ultra(buf, size, complexity)
        if not success:
            raise RuntimeError("maxrng_ultra failed")
        return bytes(buf)

    def maxrng_threadsafe(self, size: int) -> bytes:
        if not self.test_threading_available():
            raise RuntimeError("Threading is not available in this RNG implementation.\n"
                               "[?] Have you called 'MaxRNG().dll.maxrng_init()' before using 'MaxRNG().maxrng_threadsafe()'.\n"
                               "[!] Best practice is to call 'MaxRNG().test_threading_available()' and only run 'MaxRNG().maxrng_threadsafe()' if the returned value is True.")

        buf = (ctypes.c_ubyte * size)()
        success = self.dll.maxrng_threadsafe(buf, size)
        if not success:
            raise RuntimeError("maxrng_threadsafe failed")
        return bytes(buf)
