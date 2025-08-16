# Process Inspection (processInspect) Module

The `processInspect` module provides comprehensive process and system metrics collection capabilities through the `ProcessMetrics` class. This class interfaces with a native DLL to collect detailed metrics about Windows processes with minimal performance overhead, offering insights beyond what's available through standard Python libraries.

## ProcessMetrics Class

### Class Description
`ProcessMetrics` is a wrapper class that interfaces with the native `processInspect` DLL to collect various system and process metrics on Windows systems. It supports both instant snapshots and time-span measurements for comprehensive performance analysis.

### Initialization
```python
metrics = ProcessMetrics()
```

When instantiating the class, it:
- Loads the appropriate DLL using the `load_dll` helper function:
  - Determines system architecture (x86/x64) automatically
  - Searches for the appropriate DLL in the standard distribution paths
  - Configures the loader to use `ctypes.CDLL` for this module's functions
- Sets up ctypes function prototypes and return types for type safety:
  - Defines appropriate argument types for all DLL functions
  - Defines appropriate return types for all DLL functions

### Constants

The class provides constants for selecting which metrics to collect:

| Constant               | Value | Description                                 |
|------------------------|-------|---------------------------------------------|
| `METRIC_WORKING_SET`   | 0x01  | Memory currently in RAM (working set)       |
| `METRIC_PRIVATE_BYTES` | 0x02  | Memory exclusively allocated to the process |
| `METRIC_PAGEFILE`      | 0x04  | Memory usage in the pagefile                |
| `METRIC_HANDLES`       | 0x08  | Number of handles open by the process       |
| `METRIC_THREADS`       | 0x10  | Number of threads in the process            |
| `METRIC_CPU_USAGE`     | 0x20  | CPU usage percentage                        |
| `METRIC_IO`            | 0x40  | I/O statistics (reads, writes)              |
| `METRIC_NET`           | 0x80  | Network statistics                          |

These constants can be combined using bitwise OR (`|`) to select multiple metrics:

```python
# Select both CPU usage and working set metrics
metrics_flags = ProcessMetrics.METRIC_CPU_USAGE | ProcessMetrics.METRIC_WORKING_SET
```

## Methods

### `start_session(pid: int, metrics: int) -> bool`

Starts a metrics collection session for a specific process.

**Parameters:**
- `pid` (int): Process ID to monitor
- `metrics` (int): Bitmask of metrics to collect, using class constants

**Returns:**
- `bool`: `True` if session started successfully, `False` otherwise

**Implementation Details:**
- Directly calls the native DLL's `start_metrics_collection` function
- Returns a boolean indicating success or failure
- Does not raise exceptions for failure, allowing for graceful handling by caller

**Example:**
```python
pm = ProcessMetrics()
success = pm.start_session(
    1234,  # PID to monitor
    ProcessMetrics.METRIC_CPU_USAGE | ProcessMetrics.METRIC_WORKING_SET
)
```

### `end_session(pid: int, metrics: int) -> dict`

Ends a previously started metrics collection session and retrieves results.

**Parameters:**
- `pid` (int): Process ID of the session to end
- `metrics` (int): Bitmask of metrics to retrieve

**Returns:**
- `dict`: Metrics collected during the session, parsed from JSON

**Raises:**
- `RuntimeError`: If metric collection fails

**Implementation Details:**
- Uses the internal `_json_call` helper to call the `end_metrics_collection` DLL function
- Provides a detailed exception if the operation fails

**Example:**
```python
pm = ProcessMetrics()
# Start session first
pm.start_session(1234, ProcessMetrics.METRIC_CPU_USAGE | ProcessMetrics.METRIC_WORKING_SET)
# ... do some work ...
# End session and get results
results = pm.end_session(1234, ProcessMetrics.METRIC_CPU_USAGE | ProcessMetrics.METRIC_WORKING_SET)
```

### `get_snapshot(pid: int, metrics: int) -> dict`

Retrieves an instant snapshot of metrics for a process without starting a session.

**Parameters:**
- `pid` (int): Process ID to query
- `metrics` (int): Bitmask of metrics to retrieve

**Returns:**
- `dict`: Current metrics snapshot, parsed from JSON

**Raises:**
- `RuntimeError`: If metric collection fails

**Implementation Details:**
- Uses the internal `_json_call` helper to call the `get_metrics_json` DLL function
- Provides a detailed exception if the operation fails

**Example:**
```python
pm = ProcessMetrics()
snapshot = pm.get_snapshot(
    1234,  # PID to monitor
    ProcessMetrics.METRIC_CPU_USAGE | 
    ProcessMetrics.METRIC_WORKING_SET | 
    ProcessMetrics.METRIC_HANDLES
)
```

### `start_monitoring(pid: int, metrics: int, interval_ms: int, duration_ms: int = -1, callback=None) -> bool`

Starts a continuous monitoring session that collects metrics at regular intervals.

**Parameters:**
- `pid` (int): Process ID to monitor
- `metrics` (int): Bitmask of metrics to collect, using class constants
- `interval_ms` (int): Interval between metric collections in milliseconds
- `duration_ms` (int, optional): Total duration to monitor in milliseconds. Use -1 for indefinite monitoring until explicitly stopped (default: -1)
- `callback` (callable, optional): Function to call with each metrics update. The callback receives a dict of the parsed metrics.

**Returns:**
- `bool`: `True` if monitoring started successfully, `False` otherwise

**Implementation Details:**
- Creates a C-compatible callback function that converts JSON data to Python dicts
- Calls the native DLL's `start_metrics_monitoring` function
- Fails if another monitoring session is already active

**Example:**
```python
def on_metrics_update(metrics_dict):
    print(f"Process {metrics_dict['name']} CPU: {metrics_dict['cpu_usage']['percent']}%")

pm = ProcessMetrics()
pm.start_monitoring(
    1234,                                  # PID to monitor
    ProcessMetrics.METRIC_CPU_USAGE | 
    ProcessMetrics.METRIC_WORKING_SET,    # Metrics to collect
    2000,                                 # Check every 2 seconds
    60000,                                # Monitor for 1 minute
    on_metrics_update                     # Callback function
)
```

### `stop_monitoring() -> bool`

Stops an active continuous monitoring session.

**Returns:**
- `bool`: `True` if monitoring was successfully stopped, `False` if no monitoring was active

**Implementation Details:**
- Calls the native DLL's `stop_metrics_monitoring` function
- Cleans up callback references when successful

**Example:**
```python
pm = ProcessMetrics()
# Start monitoring first
pm.start_monitoring(1234, ProcessMetrics.METRIC_CPU_USAGE, 1000)
# Later, stop monitoring
if pm.stop_monitoring():
    print("Monitoring stopped successfully")
else:
    print("No active monitoring to stop")
```

### `is_monitoring_active() -> bool`

Checks if a continuous monitoring session is currently active.

**Returns:**
- `bool`: `True` if monitoring is active, `False` otherwise

**Implementation Details:**
- Calls the native DLL's `is_metrics_monitoring_active` function

**Example:**
```python
pm = ProcessMetrics()
if pm.is_monitoring_active():
    print("Monitoring is currently running")
else:
    print("No active monitoring session")
```

<details>
<summary>Internal Method</summary>

### `_json_call(func, pid: int, metrics: int, _buffer_size: int = 4096) -> dict`
<p>Internal helper method that calls a DLL function returning JSON data in a buffer, parses it, and returns it as a Python dictionary.</p>

<h4>Parameters:</h4>
<ul>
  <li><code>func</code> (<em>callable</em>): DLL function to call, which fills a buffer with JSON.</li>
  <li><code>pid</code> (<em>int</em>): Process ID to query.</li>
  <li><code>metrics</code> (<em>int</em>): Bitmask of metrics flags to request.</li>
  <li><code>_buffer_size</code> (<em>int</em>): Size of the buffer for JSON data (<strong>default:</strong> 4096 bytes).</li>
</ul>

<blockquote>
  It is strongly discouraged to modify the <code>_buffer_size</code> unless necessary, as an incorrect size can cause data truncation or wasted memory.
</blockquote>

<h4>Returns:</h4>
<ul>
  <li><code>dict</code>: Parsed JSON metrics.</li>
</ul>

<h4>Raises:</h4>
<ul>
  <li><code>RuntimeError</code>: If the DLL function call fails.</li>
</ul>

<h4>Implementation Details:</h4>
<ul>
  <li>Allocates a UTF-8 string buffer of the given size (default: 4KB).</li>
  <li>Invokes the DLL function with <code>pid</code>, metrics flags, buffer pointer, and buffer size.</li>
  <li>Checks the return value for success.</li>
  <li>Decodes the buffer content from UTF-8.</li>
  <li>Parses the JSON string into a Python dictionary.</li>
  <li>Returns the dictionary on success; raises an error on failure.</li>
</ul>

</details>

### Return Value Structure

All methods that return metrics provide a dictionary with the following structure (keys present depend on requested metrics):

```json
{
  "pid": 1234,                    // Process ID
  "name": "example.exe",          // Process name
  "timestamp": 1629384756,        // Unix timestamp
  "duration": 5.23,               // Duration in seconds (for session metrics)
  "cpu_usage": {                  // If METRIC_CPU_USAGE requested
    "percent": 14.5,              // CPU usage percentage
    "kernel_time": 0.234,         // Time spent in kernel mode (seconds)
    "user_time": 1.456            // Time spent in user mode (seconds)
  },
  "memory": {                     // Memory metrics
    "working_set": 123456789,     // If METRIC_WORKING_SET requested (bytes)
    "private_bytes": 98765432,    // If METRIC_PRIVATE_BYTES requested (bytes)
    "pagefile": 45678912          // If METRIC_PAGEFILE requested (bytes)
  },
  "handles": 345,                 // If METRIC_HANDLES requested
  "threads": 12,                  // If METRIC_THREADS requested
  "io": {                         // If METRIC_IO requested
    "reads": 1234,                // Number of read operations
    "writes": 5678,               // Number of write operations
    "bytes_read": 12345678,       // Total bytes read
    "bytes_written": 87654321     // Total bytes written
  },
  "network": {                    // If METRIC_NET requested
    "bytes_sent": 123456,         // Total bytes sent
    "bytes_received": 654321      // Total bytes received
  }
}
```

### Error Handling

The class implements robust error handling:

- **Buffer Allocation**: Creates appropriately sized buffers for JSON responses
- **Return Value Checking**: Verifies all DLL function calls succeed
- **Exception Handling**: Raises descriptive RuntimeError with process ID on failure
- **JSON Parsing**: Safely decodes and parses JSON data from the native DLL

## Usage Best Practices

### Selecting the Right Method

- **For a single point-in-time measurement:**
  ```python
  snapshot = metrics.get_snapshot(pid, metrics_flags)
  ```

- **For measuring performance over time:**
  ```python
  metrics.start_session(pid, metrics_flags)
  # ... time passes ...
  results = metrics.end_session(pid, metrics_flags)
  ```

- **For continuous monitoring with callbacks:**
  ```python
  def metrics_callback(data):
      print(f"CPU: {data['cpu_usage']['percent']}%")
  
  metrics.start_monitoring(pid, metrics_flags, 1000, callback=metrics_callback)
  # ... application continues ...
  metrics.stop_monitoring()  # When done
  ```

### Efficient Metric Collection

Combine only the metrics you need to minimize overhead:

```python
# Only collect CPU and memory metrics
flags = ProcessMetrics.METRIC_CPU_USAGE | ProcessMetrics.METRIC_WORKING_SET
```

> [!TIP]
> Some metrics cannot be collected in snapshot mode (e.g., `METRIC_CPU_USAGE`).
> 
> While other metrics can give false readings in snapshot mode (e.g., `METRIC_IO`)
> 
> So make sure to decide flag usage properly and based on your needs - This will help you avoid unnecessary overhead and ensure accurate readings.

### Error Handling

Always handle potential errors:

```python
try:
    results = metrics.get_snapshot(pid, metrics_flags)
except (RuntimeError, FileNotFoundError) as e:
    print(f"Error collecting metrics: {e}")
```

### Monitoring Best Practices

- **Interval Selection**: Choose an appropriate interval that balances data granularity with performance overhead. Very short intervals (< 100ms) may impact system performance.
- **Callback Efficiency**: Keep callback functions lightweight and fast. Heavy processing in callbacks may cause monitoring to fall behind.
- **Resource Cleanup**: Always call `stop_monitoring()` when done to release DLL resources.
- **Check Active Status**: Use `is_monitoring_active()` to verify the monitoring state when needed.

```python
# Complete monitoring example with proper resource management
try:
    pm = ProcessMetrics()
    pm.start_monitoring(pid, metrics_flags, 2000)  # 2-second interval
    
    # Do other work while monitoring happens in background
    
    # When finished:
    if pm.is_monitoring_active():
        pm.stop_monitoring()
except Exception as e:
    print(f"Monitoring error: {e}")
```
