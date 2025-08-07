import ctypes
import os
import json
import platform
from ctypes import c_char_p, c_size_t, c_ulong, create_string_buffer


class ProcessMetrics:
    """
    Wrapper class for interfacing with the native `processInspect` DLL that collects
    various system and process metrics on Windows. Supports querying working set,
    private bytes, pagefile usage, handle count, thread count, CPU usage, IO stats,
    and network stats.

    The correct DLL is selected automatically based on the platform architecture (x64 or x86),
    searching multiple possible relative paths.

    Methods allow starting a metric collection session, ending it (to retrieve final metrics),
    and getting an instant snapshot of metrics. All metric results are returned as parsed JSON dicts.

    Attributes:
        METRIC_WORKING_SET (int): Flag for working set memory usage.
        METRIC_PRIVATE_BYTES (int): Flag for private bytes memory usage.
        METRIC_PAGEFILE (int): Flag for pagefile usage.
        METRIC_HANDLES (int): Flag for handle count.
        METRIC_THREADS (int): Flag for thread count.
        METRIC_CPU_USAGE (int): Flag for CPU usage percentage.
        METRIC_IO (int): Flag for I/O statistics.
        METRIC_NET (int): Flag for network statistics.

    Raises:
        RuntimeError: If the DLL is not found or if metric collection fails.
    """

    METRIC_WORKING_SET = 0x01
    METRIC_PRIVATE_BYTES = 0x02
    METRIC_PAGEFILE = 0x04
    METRIC_HANDLES = 0x08
    METRIC_THREADS = 0x10
    METRIC_CPU_USAGE = 0x20
    METRIC_IO = 0x40
    METRIC_NET = 0x80

    def __init__(self):
        """
        Initialize ProcessMetrics instance by loading the appropriate DLL
        for the current platform architecture.

        Searches for DLL in relative paths:
            - ./dist/{arch}/processInspect_{arch}.dll
            - ../dist/{arch}/processInspect_{arch}.dll
            - ../../dist/{arch}/processInspect_{arch}.dll

        Raises:
            FileNotFoundError: If the DLL cannot be found in any of the expected locations.
        """
        arch = 'x64' if platform.architecture()[0] == '64bit' else 'x86'
        dll_name = f'processInspect_{arch}.dll'
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
            # Could not find DLL, raise an informative error
            raise FileNotFoundError(
                f"Could not find {dll_name} DLL in any of the expected locations:\n" +
                "\n".join(os.path.abspath(p) for p in possible_dist_paths)
            )

        # Load the DLL using ctypes
        self._dll = ctypes.CDLL(dll_path)

        # Define argument and return types of DLL functions for type safety
        self._dll.start_metrics_collection.argtypes = [c_ulong, c_ulong]
        self._dll.start_metrics_collection.restype = ctypes.c_int

        self._dll.end_metrics_collection.argtypes = [c_ulong, c_ulong, c_char_p, c_size_t]
        self._dll.end_metrics_collection.restype = ctypes.c_int

        self._dll.get_metrics_json.argtypes = [c_ulong, c_ulong, c_char_p, c_size_t]
        self._dll.get_metrics_json.restype = ctypes.c_int

    @staticmethod
    def _json_call(func, pid: int, metrics: int) -> dict:
        """
        Internal helper method to call a DLL function that returns JSON data
        in a buffer, parse it, and return as a Python dictionary.

        Args:
            func (callable): DLL function to call, which fills a buffer with JSON.
            pid (int): Process ID to query.
            metrics (int): Bitmask of metrics flags to request.

        Returns:
            dict: Parsed JSON metrics.

        Raises:
            RuntimeError: If the DLL function call returns failure.
        """
        buf = create_string_buffer(4096)  # buffer size fixed to 4 KB
        success = func(pid, metrics, buf, ctypes.sizeof(buf))
        if not success:
            raise RuntimeError(f"Metric collection failed for PID {pid}")
        return json.loads(buf.value.decode('utf-8'))

    def start_session(self, pid: int, metrics: int) -> bool:
        """
        Start a metrics collection session for a specific process ID.

        Args:
            pid (int): Process ID to start metrics collection for.
            metrics (int): Bitmask of metrics to collect (use class flags).

        Returns:
            bool: True if session started successfully, False otherwise.
        """
        return bool(self._dll.start_metrics_collection(pid, metrics))

    def end_session(self, pid: int, metrics: int) -> dict:
        """
        End a previously started metrics collection session and retrieve results.

        Args:
            pid (int): Process ID of the session.
            metrics (int): Bitmask of metrics to retrieve.

        Returns:
            dict: Metrics collected during the session.
        """
        return self._json_call(self._dll.end_metrics_collection, pid, metrics)

    def get_snapshot(self, pid: int, metrics: int) -> dict:
        """
        Retrieve an instant snapshot of metrics for a process without starting a session.

        Args:
            pid (int): Process ID to query.
            metrics (int): Bitmask of metrics to retrieve.

        Returns:
            dict: Current metrics snapshot.
        """
        return self._json_call(self._dll.get_metrics_json, pid, metrics)
