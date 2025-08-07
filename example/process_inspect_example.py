import os

from pyCTools.processInspect import ProcessMetrics

metrics = ProcessMetrics()
pid = os.getpid()  # Replace with your actual target PID
flags = (
        ProcessMetrics.METRIC_WORKING_SET |
        ProcessMetrics.METRIC_PRIVATE_BYTES |
        ProcessMetrics.METRIC_CPU_USAGE |
        ProcessMetrics.METRIC_IO |
        ProcessMetrics.METRIC_THREADS |
        ProcessMetrics.METRIC_HANDLES
)

# Start session
if metrics.start_session(pid, flags):
    # Simulate some work to collect metrics
    # Time await without work
    import time
    time.sleep(5)

    for i in range(3):
        # Simulate resource intensive work
        _ = [x ** 2 for x in range(10**6)]

    # End session and get metrics delta
    result = metrics.end_session(pid, flags)
    print("Delta Metrics:", result)
else:
    print("Failed to start metrics session.")

# Or get a snapshot instead
try:
    # Some values will be unreliable if it's a snapshot, example CPU usage
    snapshot = metrics.get_snapshot(pid, flags)
    print("Instant Snapshot:", snapshot)
except RuntimeError as e:
    print("Error:", str(e))
