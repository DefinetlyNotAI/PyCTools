import os
import threading

from tqdm import tqdm

import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from pyCTools.hwrng import MaxRNG

# Initialize the MaxRNG instance
rng = MaxRNG()
rng.dll.maxrng_init()


def worker(size, index, results):
    try:
        data = rng.maxrng_threadsafe(size)
        results[index] = data
    except RuntimeError as e:
        results[index] = e


def save_random_samples(total_bytes=10_000_000, chunk_size=1024):
    bytes_generated = 0

    with open("rng_output.bin", "wb") as f, tqdm(total=total_bytes, unit="B", unit_scale=True,
                                                 desc="Saving random samples") as pbar:
        while bytes_generated < total_bytes:
            num_cores = os.cpu_count() or 1
            num_threads_ = min(num_cores, (total_bytes - bytes_generated + chunk_size - 1) // chunk_size)

            results = [None] * num_threads_
            threads_ = []
            for i_ in range(num_threads_):
                size = min(chunk_size, total_bytes - bytes_generated - i_ * chunk_size)
                t_ = threading.Thread(target=worker, args=(size, i_, results))
                threads_.append(t_)
                t_.start()
            for t_ in threads_:
                t_.join()
            for i_, result_ in enumerate(results):
                if isinstance(result_, Exception):
                    raise result_
                f.write(result_)
                bytes_generated += len(result_)
                pbar.update(len(result_))
    print(f"Saved {bytes_generated} bytes to rng_output.bin")


save_random_samples()
print("Random samples saved to rng_output.bin")
