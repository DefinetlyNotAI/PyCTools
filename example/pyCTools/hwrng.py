"""
hwrng.py

Hardware Random Number Generator interface for Python using ctypes and the new hRng.dll.
"""

import ctypes
import os
import platform

__all__ = [
    "get_hardware_random_bytes",
    "get_hardware_random_bytes_extended",
    "hardware_rng_selftest",
    "HardwareRNGError"
]


class HardwareRNGError(RuntimeError):
    """Raised when hardware RNG fails or DLL cannot be loaded."""
    def __init__(self, message="Hardware RNG error occurred"):
        super().__init__(message)


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

    dll = ctypes.CDLL(dll_path)

    # Setup function signatures
    MaxRNG = dll.MaxRNG
    MaxRNG.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
    MaxRNG.restype = ctypes.c_int

    MaxRNG_ThreadSafe = dll.MaxRNG_ThreadSafe
    MaxRNG_ThreadSafe.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
    MaxRNG_ThreadSafe.restype = ctypes.c_int

    MaxRNG_Extended = dll.MaxRNG_Extended
    MaxRNG_Extended.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_int]
    MaxRNG_Extended.restype = ctypes.c_int

    RNG_SelfTest = dll.RNG_SelfTest
    RNG_SelfTest.argtypes = []
    RNG_SelfTest.restype = ctypes.c_int

    return MaxRNG, MaxRNG_ThreadSafe, MaxRNG_Extended, RNG_SelfTest


# Load the functions only once
_MaxRNG, _MaxRNG_ThreadSafe, _MaxRNG_Extended, _RNG_SelfTest = _load_rng_functions()


def get_hardware_random_bytes(size: int) -> bytes:
    """
    Retrieve cryptographically secure random bytes from MaxRNG.

    Args:
        size (int): Number of random bytes to generate.

    Returns:
        bytes: Random bytes.

    Raises:
        ValueError: If size is not positive.
        HardwareRNGError: If the RNG fails.
    """
    if size <= 0:
        raise ValueError("Size must be a positive integer")

    buffer = (ctypes.c_ubyte * size)()
    success = _MaxRNG(buffer, size)
    if not success:
        raise HardwareRNGError("MaxRNG failed.")
    return bytes(buffer)


# TODO Benchmark all with proper graphs and tests
def get_hardware_random_bytes_extended(size: int, intensive_level: int = 2) -> bytes:
    """
    Retrieve random bytes using MaxRNG_Extended.

    Args:
        size (int): Number of random bytes to generate.
        intensive_level (int): Entropy gathering intensity (>=1).

    Returns:
        bytes: Random bytes.

    Raises:
        ValueError: If size or intensive_level is not positive.
        HardwareRNGError: If the RNG fails.
    """
    if size <= 0:
        raise ValueError("Size must be a positive integer")
    if intensive_level < 1:
        raise ValueError("intensive_level must be >= 1")

    buffer = (ctypes.c_ubyte * size)()
    success = _MaxRNG_Extended(buffer, size, intensive_level)
    if not success:
        raise HardwareRNGError("MaxRNG_Extended failed.")
    return bytes(buffer)


def hardware_rng_selftest() -> bool:
    """
    Run the RNG self-test.

    Returns:
        bool: True if self-test passes, False otherwise.
    """
    return bool(_RNG_SelfTest())
