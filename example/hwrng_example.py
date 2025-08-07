# Optional CLI usage
from pyCTools.hwrng import get_hardware_random_bytes

if __name__ == '__main__':
    try:
        rb = get_hardware_random_bytes(256)
        print("Random bytes:", rb.hex())
    except Exception as e:
        print("Error:", e)
