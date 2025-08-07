"""
hwrng_example.py

Hardware Random Number Generator (RDRAND) interface for Python using ctypes and a custom DLL.
"""

import ctypes
import os
import platform

__all__ = ["get_hardware_random_bytes", "HardwareRNGError"]


class HardwareRNGError(RuntimeError):
    """Raised when hardware RNG fails or DLL cannot be loaded."""
    pass


def _load_rng_function():
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

    # Setup and return the function
    func = dll.read_hwrng
    func.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
    func.restype = ctypes.c_int
    return func


# Load the function only once
_read_hwrng = _load_rng_function()


def get_hardware_random_bytes(size: int) -> bytes:
    """
        Retrieve cryptographically secure random bytes from the hardware RNG via a custom DLL.

        Args:
            size (int): The number of random bytes to generate. Must be a positive integer.

        Returns:
            bytes: A bytes object containing `size` random bytes from the hardware RNG.

        Raises:
            ValueError: If `size` is not a positive integer.
            HardwareRNGError: If the hardware RNG fails or is not supported on this system.

        Example:
            >>> random_bytes = get_hardware_random_bytes(16)
            >>> len(random_bytes)
            16
    """
    if size <= 0:
        raise ValueError("Size must be a positive integer")

    buffer = (ctypes.c_ubyte * size)()
    success = _read_hwrng(buffer, size)

    if not success:
        raise HardwareRNGError("Hardware RNG failed or RDRAND not supported.")

    return bytes(buffer)
