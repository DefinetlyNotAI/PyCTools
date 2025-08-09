import os
import threading
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from pyCTools import MaxRNG

rng = MaxRNG()
rng.dll.maxrng_init()  # Initialize the RNG for threads, Without this threading will raise RuntimeError

print("RDRAND supported:", rng.test_rng_available())
print("Threading available:", rng.test_threading_available())

print("Basic RNG 32 bytes:", rng.maxrng(32).hex())
print("Ultra RNG 32 bytes (complexity 10):", rng.maxrng_ultra(32, 10).hex())
print("Solo Thread-safe RNG 32 bytes:", rng.maxrng_threadsafe(32).hex())


def worker(size, index, results):
    try:
        data = rng.maxrng_threadsafe(size)
        results[index] = data
    except RuntimeError as e:
        results[index] = e


num_threads = 5
bytes_per_thread = 16
results_main = [None] * num_threads
threads = []

for i in range(num_threads):
    t = threading.Thread(target=worker, args=(bytes_per_thread, i, results_main))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

for i, result in enumerate(results_main):
    if isinstance(result, Exception):
        print(f"Thread {i}: RNG failed: {result}")
    else:
        print(f"Thread {i}: got {len(result)} bytes -> {result.hex()}")

print("All threads finished.")


print("Example completed successfully.")
