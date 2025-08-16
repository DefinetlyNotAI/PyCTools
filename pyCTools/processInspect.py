import ctypes
import json
from ctypes import c_char_p, c_size_t, c_ulong, create_string_buffer, CFUNCTYPE, c_void_p, c_int

from pyCTools._loadDLL import load_dll


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
        """
        # Load the DLL using ctypes
        self._dll = load_dll(dll_prefix_name="processInspect", dll_load_func=ctypes.CDLL)

        # Define argument and return types of DLL functions for type safety
        self._dll.start_metrics_collection.argtypes = [c_ulong, c_ulong]
        self._dll.start_metrics_collection.restype = ctypes.c_int

        self._dll.end_metrics_collection.argtypes = [c_ulong, c_ulong, c_char_p, c_size_t]
        self._dll.end_metrics_collection.restype = ctypes.c_int

        self._dll.get_metrics_json.argtypes = [c_ulong, c_ulong, c_char_p, c_size_t]
        self._dll.get_metrics_json.restype = ctypes.c_int

        # Define C function type for the monitoring callback
        self._CALLBACK_TYPE = CFUNCTYPE(None, c_char_p, c_void_p)

        # Set types for monitoring functions
        self._dll.start_metrics_monitoring.argtypes = [c_ulong, c_ulong, c_ulong, c_int,
                                                       self._CALLBACK_TYPE, c_void_p]
        self._dll.start_metrics_monitoring.restype = ctypes.c_int

        self._dll.stop_metrics_monitoring.argtypes = []
        self._dll.stop_metrics_monitoring.restype = ctypes.c_int

        self._dll.is_metrics_monitoring_active.argtypes = []
        self._dll.is_metrics_monitoring_active.restype = ctypes.c_int

        # Store callback reference to prevent garbage collection
        self._callback_ref = None
        self._user_callback = None

    @staticmethod
    def _json_call(func, pid: int, metrics: int, _buffer_size: int = 4096) -> dict:
        """
        Internal helper method to call a DLL function that returns JSON data
        in a buffer, parse it, and return as a Python dictionary.

        Args:
            func (callable): DLL function to call, which fills a buffer with JSON.
            pid (int): Process ID to query.
            metrics (int): Bitmask of metrics flags to request.
            _buffer_size (int): Size of the buffer to hold JSON data (default 4096 bytes).

        Returns:
            dict: Parsed JSON metrics.

        Raises:
            RuntimeError: If the DLL function call returns failure.
        """
        buf = create_string_buffer(_buffer_size)  # buffer size fixed to 4 KB
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

    # noinspection PyUnusedLocal
    def _callback_wrapper(self, json_str, user_data):
        """
        Internal callback wrapper that converts C JSON string to Python dict
        and calls the user's callback function.

        Args:
            json_str (c_char_p): JSON metrics data from C.
            user_data (c_void_p): User data pointer (unused in this implementation).
        """
        if self._user_callback:
            metrics_dict = json.loads(ctypes.string_at(json_str).decode('utf-8'))
            self._user_callback(metrics_dict)

    def start_monitoring(self, pid: int, metrics: int, interval_ms: int,
                         duration_ms: int = -1, callback=None) -> bool:
        """
        Start continuous monitoring of a process at specified intervals.

        Args:
            pid (int): Process ID to monitor.
            metrics (int): Bitmask of metrics to collect (use class flags).
            interval_ms (int): Interval between metric collections in milliseconds.
            duration_ms (int): Total duration to monitor in milliseconds. Use -1 for
                               indefinite monitoring until explicitly stopped.
            callback (callable): Function to call with each metrics update.
                                The callback receives a dict of the parsed metrics.

        Returns:
            bool: True if monitoring started successfully, False otherwise.
        """
        if self.is_monitoring_active():
            return False

        self._user_callback = callback

        # Create C-compatible callback function
        if callback:
            self._callback_ref = self._CALLBACK_TYPE(self._callback_wrapper)
        else:
            self._callback_ref = None

        return bool(self._dll.start_metrics_monitoring(
            pid, metrics, interval_ms, duration_ms, self._callback_ref, None))

    def stop_monitoring(self) -> bool:
        """
        Stop an active monitoring session.

        Returns:
            bool: True if monitoring was successfully stopped, False if no monitoring was active.
        """
        result = bool(self._dll.stop_metrics_monitoring())
        if result:
            self._user_callback = None
            self._callback_ref = None
        return result

    def is_monitoring_active(self) -> bool:
        """
        Check if a monitoring session is currently active.

        Returns:
            bool: True if monitoring is active, False otherwise.
        """
        return bool(self._dll.is_metrics_monitoring_active())
