import math


def shannon_entropy(data: bytes):
    if not data:
        return None
    freq = {}
    for b in data:
        freq[b] = freq.get(b, 0) + 1
    entropy = 0.0
    length = len(data)
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    print(f"Shannon Entropy:")
    print(f"    {entropy:.4f} bits per byte")
    return None


def frequency_test(data: bytes):
    zeros = sum(bin(b).count("0") for b in data)
    ones = sum(bin(b).count("1") for b in data)
    print("Frequency test:")
    print(f"    Total bits: {len(data) * 8}")
    print(f"    Zeros: {zeros}")
    print(f"    Ones: {ones}")


def runs_test(data: bytes):
    bits = ''.join(f'{b:08b}' for b in data)
    runs = 1
    prev_bit = bits[0]

    run_lengths = []
    current_run_length = 1

    for bit in bits[1:]:
        if bit == prev_bit:
            current_run_length += 1
        else:
            run_lengths.append(current_run_length)
            current_run_length = 1
            runs += 1
        prev_bit = bit
    run_lengths.append(current_run_length)

    avg_run_length = sum(run_lengths) / len(run_lengths)
    max_run_length = max(run_lengths)
    min_run_length = min(run_lengths)

    print("Runs test:")
    print(f"    Runs: {runs}")
    print(f"    Avg run length: {avg_run_length:.2f}")
    print(f"    Max run length: {max_run_length}")
    print(f"    Min run length: {min_run_length}")


def autocorrelation_test(data: bytes, lag=1):
    bits = ''.join(f'{b:08b}' for b in data)
    n = len(bits)
    matches = 0
    for i in range(n - lag):
        if bits[i] == bits[i + lag]:
            matches += 1
    autocorr = matches / (n - lag)
    print(f"Autocorrelation test (lag={lag}):")
    print(f"    Autocorrelation: {autocorr:.4f} (expected ~0.5)")


def bit_position_frequency(data: bytes):
    print("Bit position frequency test:")
    counts = [0] * 8  # count of set bits per position
    total_bytes = len(data)

    for b in data:
        for i in range(8):
            if b & (1 << i):
                counts[i] += 1

    for i, c in enumerate(counts):
        freq = c / total_bytes
        print(f"    Bit position {i}: set bit frequency = {freq:.4f} (expected ~0.5)")


def main():
    print("-" * 40)
    print("Starting RNG tests...")
    print("-" * 40 + "\n")
    filename = "rng_output.bin"
    with open(filename, "rb") as f:
        data = f.read()

    print(f"Read {len(data)} bytes from {filename}\n")

    print("-" * 40)
    shannon_entropy(data)
    print("-" * 40)
    frequency_test(data)
    print("-" * 40)
    runs_test(data)
    print("-" * 40)
    autocorrelation_test(data, lag=1)
    print("-" * 40)
    autocorrelation_test(data, lag=8)
    print("-" * 40)
    bit_position_frequency(data)
    print("-" * 40)
    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
