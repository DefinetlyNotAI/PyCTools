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

---

# Example script

This is a comprehensive script that can be used to fully test `process_inspect` properly

<details>
<summary>Example code for `process_inspect`</summary>

```python
"""
Comprehensive example demonstrating all features of ProcessMetrics from the pyCTools module.

This example shows:
1. Setting up the ProcessMetrics module
2. Using both session-based and snapshot monitoring approaches
3. Working with all available metric types
4. Interpreting and displaying the collected metrics
5. Proper error handling and best practices
"""
import json
import os
import random
import time
from typing import Dict, Any

from pyCTools import ProcessMetrics


def print_json(data: Dict[str, Any], title: str = None) -> None:
    """Helper function to print JSON data in a formatted way."""
    if title:
        print(f"\n===== {title} =====")
    print(json.dumps(data, indent=2))


def simulate_workload(intensity: int = 1) -> None:
    """
    Simulate different types of system workload to demonstrate metric changes.

    Args:
        intensity: Level of workload (1-3)
    """
    # CPU-intensive work
    print(f"Simulating CPU-intensive work (level {intensity})...")
    _ = [x ** 2 for x in range(intensity * 10**6)]

    # Memory-intensive work
    print(f"Simulating memory-intensive work (level {intensity})...")
    # noinspection PyUnusedLocal
    big_list = [random.random() for _ in range(intensity * 10**5)]

    # I/O-intensive work (file operations)
    print(f"Simulating I/O-intensive work (level {intensity})...")
    temp_filename = "temp_workload_file.txt"
    with open(temp_filename, "w") as f:
        for i in range(intensity * 100):
            f.write(f"Line {i}: " + "X" * 1000 + "\n")

    # Read the file back
    with open(temp_filename, "r") as f:
        _ = f.read()

    # Clean up
    os.remove(temp_filename)

    # Force garbage collection to show memory changes
    import gc
    gc.collect()


def demo_session_based_monitoring() -> None:
    """
    Demonstrates how to use session-based monitoring with ProcessMetrics.

    Session-based monitoring is ideal for:
    - Measuring changes over specific periods of time
    - Calculating deltas (differences) between start and end points
    - Getting accurate CPU usage measurements
    """
    print("\n\n" + "=" * 80)
    print("DEMONSTRATION: SESSION-BASED MONITORING")
    print("=" * 80)

    metrics = ProcessMetrics()
    pid = os.getpid()  # Monitor the current Python process

    # Use ALL available metrics flags by combining them with bitwise OR
    # Each flag represents a category of metrics to collect
    flags = (
            ProcessMetrics.METRIC_WORKING_SET |    # Memory currently in RAM
            ProcessMetrics.METRIC_PRIVATE_BYTES |  # Memory exclusively used by the process
            ProcessMetrics.METRIC_PAGEFILE |       # Swap file usage
            ProcessMetrics.METRIC_HANDLES |        # OS resource handles count
            ProcessMetrics.METRIC_THREADS |        # Thread count information
            ProcessMetrics.METRIC_CPU_USAGE |      # CPU utilization percentage
            ProcessMetrics.METRIC_IO |             # I/O operations statistics
            ProcessMetrics.METRIC_NET              # Network usage statistics
    )

    print(f"Starting metrics session for PID {pid} with all metrics enabled")
    print("Session-based monitoring captures changes between start and end points")

    # Start the metrics collection session
    if not metrics.start_session(pid, flags):
        print("ERROR: Failed to start metrics session. The process may not exist or you may not have sufficient permissions.")
        return

    print("Session started successfully. Performing workloads...")

    # Simulate different workloads to show their impact on metrics
    # First a baseline idle period
    print("\nPHASE 1: Idle period (5 seconds) to establish baseline")
    time.sleep(5)

    # Then perform progressively more intensive operations
    print("\nPHASE 2: Low-intensity workload")
    simulate_workload(intensity=1)

    print("\nPHASE 3: Medium-intensity workload")
    simulate_workload(intensity=2)

    print("\nPHASE 4: High-intensity workload")
    simulate_workload(intensity=3)

    # End the session and get the delta metrics
    print("\nEnding metrics session and collecting results...")
    try:
        result = metrics.end_session(pid, flags)
        print_json(result, "SESSION METRICS (DELTA BETWEEN START AND END)")

        # Explain some key metrics
        print("\n--- KEY METRICS EXPLAINED ---")

        if "cpu" in result:
            usage = result["cpu"]["usage"] if isinstance(result["cpu"], dict) else result["cpu"]
            print(f"CPU Usage: {usage}% - Percentage of CPU time used by this process")

        if "memory" in result:
            memory = result["memory"]
            print(f"Working Set: {memory.get('working_set', 'N/A')} bytes - Memory currently in physical RAM")
            print(f"Private Bytes: {memory.get('private_bytes', 'N/A')} bytes - Memory exclusively allocated to this process")
            if "pagefile" in memory:
                print(f"Pagefile Usage: {memory['pagefile']} bytes - Amount of swap file used")

        if "io" in result:
            io = result["io"]
            print(f"Read Operations: {io.get('read_operations', 'N/A')} - Number of read operations performed")
            print(f"Write Operations: {io.get('write_operations', 'N/A')} - Number of write operations performed")
            print(f"Read Bytes: {io.get('read_bytes', 'N/A')} bytes - Total bytes read from disk")
            print(f"Write Bytes: {io.get('write_bytes', 'N/A')} bytes - Total bytes written to disk")

        if "threads" in result:
            threads = result["threads"]
            if isinstance(threads, dict):
                print(f"Thread Count: {threads.get('count', 'N/A')} - Number of threads in this process")
            else:
                print(f"Thread Count: {threads} - Number of threads in this process")
            if "handles" in result:
                handles = result["handles"]
                if isinstance(handles, dict):
                    print(f"Handle Count: {handles.get('count', 'N/A')} - Number of OS resource handles")
                else:
                    print(f"Handle Count: {handles} - Number of OS resource handles")
    except RuntimeError as e:
        print(f"Error ending metrics session: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


def demo_snapshot_monitoring() -> None:
    """
    Demonstrates how to use snapshot-based monitoring with ProcessMetrics.

    Snapshot-based monitoring is useful for:
    - Getting immediate metrics without having to start/end a session
    - Polling metrics at regular intervals
    - Getting a quick overview of current process state

    Note: Some metrics like CPU usage may be less accurate in snapshot mode
    """
    print("\n\n" + "=" * 80)
    print("DEMONSTRATION: SNAPSHOT-BASED MONITORING")
    print("=" * 80)

    metrics = ProcessMetrics()
    pid = os.getpid()  # Monitor the current Python process

    # Define the metrics we want to collect
    flags = (
            ProcessMetrics.METRIC_WORKING_SET |
            ProcessMetrics.METRIC_PRIVATE_BYTES |
            ProcessMetrics.METRIC_PAGEFILE |
            ProcessMetrics.METRIC_HANDLES |
            ProcessMetrics.METRIC_THREADS |
            ProcessMetrics.METRIC_CPU_USAGE |
            ProcessMetrics.METRIC_IO |
            ProcessMetrics.METRIC_NET
    )

    print(f"Taking metrics snapshots for PID {pid}")
    print("This approach provides immediate data about the current state")
    print("Note: CPU usage may be less accurate in snapshot mode compared to session mode\n")

    # Take an initial snapshot before any work
    try:
        print("Taking initial snapshot...")
        snapshot1 = metrics.get_snapshot(pid, flags)
        print_json(snapshot1, "INITIAL SNAPSHOT")
    except RuntimeError as e:
        print(f"Error taking initial snapshot: {str(e)}")
        return

    # Perform some work to change metrics
    print("\nPerforming intensive workload...")
    simulate_workload(intensity=3)

    # Take another snapshot after work
    try:
        print("\nTaking snapshot after workload...")
        snapshot2 = metrics.get_snapshot(pid, flags)
        print_json(snapshot2, "POST-WORKLOAD SNAPSHOT")

        # Calculate and display some differences manually
        print("\n--- MANUAL DIFFERENCE CALCULATION ---")
        if "memory" in snapshot1 and "memory" in snapshot2:
            ws_diff = snapshot2["memory"].get("working_set", 0) - snapshot1["memory"].get("working_set", 0)
            pb_diff = snapshot2["memory"].get("private_bytes", 0) - snapshot1["memory"].get("private_bytes", 0)
            print(f"Working Set Change: {ws_diff} bytes")
            print(f"Private Bytes Change: {pb_diff} bytes")

        if "handles" in snapshot1 and "handles" in snapshot2:
            handle1 = snapshot1["handles"]["count"] if isinstance(snapshot1["handles"], dict) else snapshot1["handles"]
            handle2 = snapshot2["handles"]["count"] if isinstance(snapshot2["handles"], dict) else snapshot2["handles"]
            handle_diff = handle2 - handle1
            print(f"Handle Count Change: {handle_diff}")
    except RuntimeError as e:
        print(f"Error taking second snapshot: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


def demo_selective_metrics() -> None:
    """
    Demonstrates how to selectively choose which metrics to collect.

    Advantages of selective metrics:
    - Reduced overhead
    - Focused data collection
    - May avoid permission issues for certain metrics
    """
    print("\n\n" + "=" * 80)
    print("DEMONSTRATION: SELECTIVE METRICS COLLECTION")
    print("=" * 80)

    metrics = ProcessMetrics()
    pid = os.getpid()

    print("You can select only the metrics you need by combining specific flags")
    print("This can reduce overhead and focus on metrics relevant to your application")

    # Example 1: Only memory metrics
    memory_flags = (
            ProcessMetrics.METRIC_WORKING_SET |
            ProcessMetrics.METRIC_PRIVATE_BYTES |
            ProcessMetrics.METRIC_PAGEFILE
    )

    print("\n--- MEMORY METRICS ONLY ---")
    try:
        memory_snapshot = metrics.get_snapshot(pid, memory_flags)
        print_json(memory_snapshot, "MEMORY METRICS")
    except RuntimeError as e:
        print(f"Error: {str(e)}")

    # Example 2: Only CPU and threads
    performance_flags = (
            ProcessMetrics.METRIC_CPU_USAGE |
            ProcessMetrics.METRIC_THREADS
    )

    print("\n--- PERFORMANCE METRICS ONLY ---")
    try:
        performance_snapshot = metrics.get_snapshot(pid, performance_flags)
        print_json(performance_snapshot, "PERFORMANCE METRICS")
    except RuntimeError as e:
        print(f"Error: {str(e)}")

    # Example 3: Only I/O and network metrics
    io_flags = (
            ProcessMetrics.METRIC_IO |
            ProcessMetrics.METRIC_NET
    )

    print("\n--- I/O METRICS ONLY ---")
    try:
        io_snapshot = metrics.get_snapshot(pid, io_flags)
        print_json(io_snapshot, "I/O METRICS")
    except RuntimeError as e:
        print(f"Error: {str(e)}")


def demo_other_process_monitoring() -> None:
    """
    Demonstrates monitoring other processes (with proper permissions).
    """
    print("\n\n" + "=" * 80)
    print("DEMONSTRATION: MONITORING OTHER PROCESSES")
    print("=" * 80)

    metrics = ProcessMetrics()

    # Get a list of processes (this is just an example, requires psutil)
    try:
        import psutil
        processes_available = True
    except ImportError:
        print("psutil not available. Install with 'pip install psutil' to see this demo")
        return

    if processes_available:
        print("Available processes (first 5):")
        for i, proc in enumerate(psutil.process_iter(['pid', 'name'])):
            if i >= 5:
                break
            print(f"  PID {proc.info['pid']}: {proc.info['name']}")

        # Try to monitor a system process like explorer.exe on Windows
        target_name = "explorer.exe" if os.name == "nt" else "sshd"
        target_pid = None

        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == target_name:
                target_pid = proc.info['pid']
                break

        if target_pid:
            print(f"\nAttempting to monitor {target_name} (PID {target_pid})")
            print("Note: This may fail due to permissions, especially on non-admin accounts")

            flags = ProcessMetrics.METRIC_WORKING_SET | ProcessMetrics.METRIC_THREADS

            try:
                snapshot = metrics.get_snapshot(target_pid, flags)
                print_json(snapshot, f"{target_name.upper()} METRICS")
            except RuntimeError as e:
                print(f"Error monitoring {target_name}: {str(e)}")
                print("This is expected if you don't have sufficient permissions")
        else:
            print(f"\nCould not find {target_name} process")


def main():
    """Main function to demonstrate all ProcessMetrics capabilities."""
    print("=" * 80)
    print("PROCESS METRICS COMPREHENSIVE DEMONSTRATION")
    print("=" * 80)
    print("\nThis example demonstrates all features of the ProcessMetrics class.")
    print("It shows how to monitor process resources in different ways and interpret the results.")

    # Demonstrate different monitoring approaches
    demo_session_based_monitoring()
    demo_snapshot_monitoring()
    demo_selective_metrics()
    demo_other_process_monitoring()

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

```

</details>
