"""
Comprehensive example demonstrating all features of ProcessMetrics from the pyCTools module.

This example shows:
1. Setting up the ProcessMetrics module
2. Using both session-based and snapshot monitoring approaches
3. Working with all available metric types
4. Interpreting and displaying the collected metrics
5. Proper error handling and best practices
"""
import os
import sys
import time
import json
import random
from typing import Dict, Any

# Add the parent directory to sys.path to import pyCTools
# This is necessary for local testing, but once pyCTools becomes a package, this can be removed.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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
        processes_available = False
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
