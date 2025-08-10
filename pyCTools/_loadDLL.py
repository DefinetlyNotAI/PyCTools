import ctypes
import os
import platform
from typing import Callable, Optional


def load_dll(
        dll_prefix_name: str,
        dll_load_func: Callable = ctypes.WinDLL,
        hardcoded_dll_location: Optional[str] = None
):
    """
    Loads a Windows DLL with architecture awareness and optional custom path.

    This function attempts to load a dynamic-link library (DLL) based on the provided prefix name,
    automatically selecting the correct architecture (x64 or x86) according to the current Python
    interpreter. The DLL is expected to be located in a subdirectory structure of the form:
    ./bin/{arch}/{dll_prefix_name}_{arch}.dll, where {arch} is either 'x64' or 'x86'.

    Alternatively, a hardcoded DLL path can be provided, in which case the function will verify
    the existence of the file at that location before attempting to load it.

    Parameters
    ----------
    dll_prefix_name : str
        The prefix of the DLL filename (e.g., 'myLibrary' for 'myLibrary_x64.dll').
    dll_load_func : Callable, optional
        The function used to load the DLL. Defaults to ctypes.WinDLL, but can be replaced with
        ctypes.CDLL or any compatible loader for testing or non-standard DLLs.
    hardcoded_dll_location : Optional[str], optional
        An explicit path to the DLL file. If provided and valid, this path is used instead of
        constructing the path from the prefix and architecture.

    Returns
    -------
    ctypes.CDLL or ctypes.WinDLL
        The loaded DLL object, as returned by the specified loader function.

    Raises
    ------
    FileNotFoundError
        If the DLL cannot be found at the constructed or provided path.
    OSError
        If the DLL fails to load due to an invalid format or missing dependencies.

    Notes
    -----
    - This function is intended for use on Windows platforms.
    - The architecture is determined by the running Python interpreter, not the OS alone.
    - The default search path assumes a project structure with DLLs in 'bin/x64' or 'bin/x86'.
    """

    # Determine system architecture to pick the correct DLL version
    arch = 'x64' if platform.architecture()[0] == '64bit' else 'x86'

    # Construct DLL filename based on prefix and architecture suffix
    dll_name = f'{dll_prefix_name}_{arch}.dll'

    # If hardcoded path is provided, use it after verifying it exists
    if hardcoded_dll_location is None:
        dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bin', arch, dll_name))
    elif os.path.isfile(hardcoded_dll_location):
        dll_path = os.path.abspath(hardcoded_dll_location)
    else:
        raise FileNotFoundError(f"Hardcoded DLL location does not exist: {hardcoded_dll_location}")

    # Load and return the DLL using the specified loading function
    return dll_load_func(dll_path)
