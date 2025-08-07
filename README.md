# Project Overview

This project provides a cross-language toolkit for Windows process inspection and hardware random number generation, with both Python and C components. It includes:

- **Python library (`pyCTools`)**: Easy-to-use wrappers for native DLLs to access process metrics and hardware RNG.
- **C source files**: Implement the DLLs for process inspection and hardware RNG.
- **Example Python scripts**: Demonstrate usage of the library.
- **PowerShell build helper**: Automates DLL compilation for x86/x64.

> [!IMPORTANT]
> To get the `dist` binary folder, choose **one** of the following options:
>
> | Method                       | Description                                                                                      | Requirements                                                   |
> |-----------------------------|--------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
> | Manual Build                | Compile the binaries yourself using `cl.exe` or similar toolchains                               | Microsoft Visual Studio with MSVC installed                    |
> | Auto Build Script           | Run the [`tool/compilerHelper.ps1`](https://github.com/DefinetlyNotAI/PyCTools/blob/main/tool/compilerHelper.ps1) PowerShell script | Visual Studio Build Tools + PowerShell                         |
> | Prebuilt Release Archive    | Download precompiled binaries from the [releases page](https://github.com/DefinetlyNotAI/PyCTools/releases/tag/v1.0.0)              | None (just extract archive)                                    |
>
> No matter what you decide, do still read the important notice about the `dist` from the [release](https://github.com/DefinetlyNotAI/PyCTools/releases/tag/v1.0.0) OR check the [Wiki](https://github.com/DefinetlyNotAI/PyCTools/wiki/DLL-Discovery) page about the DLL discovery explanation.

## Directory Structure

<details>
  <summary>📁 Project Structure (click to expand)</summary>

    example/
      pyCTools/
        hwrng.py           # Python wrapper for hardware RNG DLL
        processInspect.py  # Python wrapper for process inspection DLL
      hwrng_example.py     # Example: hardware RNG usage
      process_inspect_example.py # Example: process metrics usage
    src/
      hRng.c               # C source for hardware RNG DLL
      processInspect.c     # C source for process inspection DLL
    tool/
      compilerHelper.ps1   # PowerShell script to build DLLs for x86/x64
    dist/
      x64/                 # Compiled DLLs for 64-bit
      x86/                 # Compiled DLLs for 32-bit

</details>

## Building the DLLs

1. Open PowerShell and run `tool/compilerHelper.ps1`.
2. Select which `.c` files to compile.
3. The script will build both x86 and x64 DLLs and place them in `dist/x86` and `dist/x64`.

## Using the Python Library

- Place the `dist/` folder as a sibling to your Python scripts or as described in the wrappers.
- Import and use `pyCTools.hwrng` or `pyCTools.processInspect` as shown in the examples.

## Example Usage

**Hardware RNG:**
```python
from pyCTools.hwrng import get_hardware_random_bytes
rb = get_hardware_random_bytes(16)
print(rb.hex())
```

**Process Inspection:**
```python
from pyCTools.processInspect import ProcessMetrics
metrics = ProcessMetrics()
pid = 1234  # Target PID
flags = ProcessMetrics.METRIC_WORKING_SET | ProcessMetrics.METRIC_CPU_USAGE
snapshot = metrics.get_snapshot(pid, flags)
print(snapshot)
```

## DLL Discovery

The Python wrappers automatically search for the correct DLL in:
- `./dist/{arch}/<dll>`
- `../dist/{arch}/<dll>`
- `../../dist/{arch}/<dll>`

where `{arch}` is `x64` or `x86` depending on your Python interpreter.

## Extra resources

> [!TIP]
> Want to dive deeper into how everything works? Head over to the [PyCTools Wiki](https://github.com/DefinetlyNotAI/PyCTools/wiki) for detailed breakdowns of the key parts:
>
> • **DLL explanations**: learn how the DLLs are structured, discovered, and loaded 
> • **Python examples, wrappers, and usage**: practical code snippets and usage patterns in Python 
> • **C code explanation**: understand the underlying native implementation

