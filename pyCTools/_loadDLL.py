import os
import platform
import ctypes
from typing import Callable, Optional, List


def load_dll(
        dll_prefix_name: str,
        dll_load_func: Callable = ctypes.WinDLL,
        possible_bin_paths: Optional[List[str]] = None,
        hardcoded_dll_location: Optional[str] = None
):
    """
    Load a DLL file based on architecture and search paths, returning the loaded DLL handle.

    This function attempts to locate and load a DLL file matching the current system's
    architecture (x86 or x64). The DLL filename is constructed by appending the architecture
    suffix to a given prefix name (e.g., "processInspect_x64.dll").

    You can specify a hardcoded absolute DLL path or provide a list of possible relative
    distribution paths to search through. If both are provided, the function raises a ValueError.

    Args:
        dll_prefix_name (str):
            The base name of the DLL without architecture or extension.
            For example, for "processInspect_x64.dll", the prefix is "processInspect".

        dll_load_func (Callable, optional):
            The function used to load the DLL, typically `ctypes.WinDLL` or `ctypes.CDLL`.
            Defaults to `ctypes.WinDLL`.

        possible_bin_paths (Optional[List[str]], optional):
            A list of possible relative paths where the DLL might reside. These are
            joined with the DLL filename and searched in order.
            Defaults to None, which triggers searching in default distribution directories.

        hardcoded_dll_location (Optional[str], optional):
            An absolute path to the DLL. If provided, this path is used exclusively,
            bypassing the search logic.

    Raises:
        ValueError:
            If both `hardcoded_dll_location` and `possible_dist_paths` are provided
            simultaneously.

        FileNotFoundError:
            If the DLL cannot be found at the specified or searched locations.

    Returns:
        ctypes.WinDLL or ctypes.CDLL:
            The loaded DLL object returned by the provided `dll_load_func`.

    Example:
        dll = load_dll("processInspect")
    """

    # Validate mutually exclusive parameters
    if hardcoded_dll_location and possible_bin_paths:
        raise ValueError("Cannot provide both hardcoded_dll_location and possible_dist_paths.")

    # Determine system architecture to pick the correct DLL version
    arch = 'x64' if platform.architecture()[0] == '64bit' else 'x86'

    # Construct DLL filename based on prefix and architecture suffix
    dll_name = f'{dll_prefix_name}_{arch}.dll'

    # Base directory is the directory where this script resides
    base_dir = os.path.abspath(os.path.dirname(__file__))

    if hardcoded_dll_location:
        # If hardcoded path is provided, use it after verifying it exists
        dll_path = os.path.abspath(hardcoded_dll_location)
        if not os.path.isfile(dll_path):
            raise FileNotFoundError(f"Hardcoded DLL location does not exist: {dll_path}")
    else:
        # If no hardcoded path, define default search paths if not provided
        if possible_bin_paths is None:
            # Common fallback directories where DLL might be located relative to this file
            possible_bin_paths = [
                os.path.join(base_dir, 'bin', arch, dll_name),
                os.path.join(base_dir, '..', 'bin', arch, dll_name),
                os.path.join(base_dir, '..', '..', 'bin', arch, dll_name),
            ]

        # Convert all candidate paths to absolute paths
        abs_paths = [os.path.abspath(p) for p in possible_bin_paths]

        # Find the first path where the DLL file actually exists
        dll_path = next((p for p in abs_paths if os.path.isfile(p)), None)

        # If no valid DLL file was found, raise error with detailed info
        if dll_path is None:
            raise FileNotFoundError(
                f"Could not find {dll_name} DLL in any of the expected locations:\n" +
                "\n".join(abs_paths)
            )

    # Inform user about which DLL path is being loaded
    print(f"Loading {dll_path} DLL...")

    # Load and return the DLL using the specified loading function
    return dll_load_func(dll_path)
