<div style="text-align: center;">
  <h1>PyCTools</h1>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
  <img src="https://img.shields.io/badge/platform-Windows-lightgray" alt="Platform" />
  <img src="https://img.shields.io/github/languages/top/DefinetlyNotAI/PyCTools" alt="Languages" />
  <img src="https://img.shields.io/github/v/tag/DefinetlyNotAI/PyCTools" alt="Version" />
</div>

> [!NOTE]
> There are multiple ways to install the pyCTools library!
>
> * **Manual installation:**
>
>   1. Clone the repository and build the DLLs yourself.
>   2. Run `python ./tools/setup.py bdist_wheel` to create the wheel file.
>   3. The setup script will show you how to install the package locally with pip and how to create a virtual environment for testing.
> * **Automatic installation:**
>   Go to the [releases page](https://github.com/DefinetlyNotAI/PyCTools/releases) and select the version you wish to install, and click on it, then copy the top `pip` command that will allow you to install it
>   [Auto installation support from v0.2.0-beta and above]


This project provides a cross-language toolkit for Windows process inspection and hardware random number generation, with both Python and C components. It includes:

- **Python library (`pyCTools`)**: Easy-to-use wrappers for native DLLs to access process metrics and hardware RNG.
- **C source files**: Implement the DLLs for process inspection and hardware RNG.
- **Example Python scripts**: Demonstrate usage of the library.
- **PowerShell build helper**: Automates DLL compilation for x86/x64.

> [!IMPORTANT]
> To get the `dist` binary folder, choose **one** of the following options:
>
> | Method                   | Description                                                                                                  | Requirements                                        |
> |--------------------------|--------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
> | Manual Build             | Compile the binaries yourself using `cl.exe` or similar toolchains                                           | Microsoft Visual Studio with MSVC installed         |
> | Auto Build Script        | Run the [`tool/compilerHelper.ps1`](tool/compilerHelper.ps1) PowerShell script                               | Visual Studio Build Tools + PowerShell              |
> | Prebuilt Release Archive | Download precompiled binaries from the [releases page](https://github.com/DefinetlyNotAI/PyCTools/releases/) | None, make sure to use the latest available version |
>
> No matter what you decide, do still read the important notice about the `dist` from the [release](https://github.com/DefinetlyNotAI/PyCTools/releases/) OR check the [Wiki](https://github.com/DefinetlyNotAI/PyCTools/wiki#dll-discovery-and-dist-directory) page about the DLL discovery explanation.

## Directory Structure

<details>
  <summary>📁 Project Structure (click to expand)</summary>

    root/
    ├── bin/                               # Auto-generated folder containing compiled DLL binaries
    │   ├── x86/                           # 32-bit DLL builds
    │   └── x64/                           # 64-bit DLL builds
    │
    ├── dist/                              # Release artifacts for distribution
    │   ├── bin.zip                        # Zipped prebuilt binaries
    │   └── bin.zip.sha256                 # SHA256 checksum for `bin.zip`
    │
    ├── examples/                          # Example Python scripts demonstrating usage
    │   ├── hwrng_example.py               # Example: Hardware RNG usage
    │   ├── process_inspect_example.py     # Example: Process inspection usage
    │   └── rng_tests/                     # RNG test scripts and outputs
    │       ├── rng_output.bin              # 10M bytes of RNG data (complexity 1, threaded)
    │       ├── rng_entropy_output.png      # PNG entropy visualization of RNG output
    │       ├── Results.txt                 # Test results from `rng_test.py`
    │       ├── rng_test.py                 # Script to test hardware RNG
    │       └── generate_bin.py             # Generates binary file from RNG
    │
    ├── pyCTools/                          # Python package (library code)
    │   ├── __init__.py                    # Package initializer
    │   ├── hwrng.py                       # Hardware RNG DLL wrapper
    │   ├── processInspect.py               # Process inspection DLL wrapper
    │   └── _loadDLL.py                     # DLL loading logic used by wrappers
    │
    ├── tool/                              # Build and distribution tools
    │   ├── compilerHelper.ps1              # Compiles C code into DLLs
    │   └── distributionHelper.ps1          # Creates `bin.zip` and SHA256 checksum
    │
    ├── src/                               # C source code for DLLs
    │   ├── hRng.c                          # Hardware RNG implementation
    │   └── processInspect.c                # Process inspection implementation
    │
    └── CMakeLists.txt                     # CMake build configuration (currently unused)

</details>

## Building the DLLs

1. Open **PowerShell** and run:
   ```powershell
   cd ./tool/
   compilerHelper.ps1
   ```
   
2. Choose the `.c` source files you want to compile.

3. The script will compile for **both x86 and x64** architectures, placing the output in:
   - `bin/x86` (32-bit builds)
   - `bin/x64` (64-bit builds)

> [!IMPORTANT]
> The build process uses `cl.exe` from the **MSVC toolchain** in Visual Studio, so make sure it’s installed and available in your PATH.
    
> [!NOTE]
> - Each compiled source produces **four files per architecture**: `.dll`, `.exp`, `.lib`, and `.obj`.
>
> - Only the `.dll` is needed by the Python library.
> 
> - DLL filenames include an architecture suffix:
>
>   - Example: `hRng_x86.dll`, `hRng_x64.dll`.

## Using the Python Library

- Place the `dist/` folder inside the `pyCTools` package directory, or at max two levels up the library.
- Import and use `hwrng` or `processInspect` from `pyCTools`.
- The library will automatically load the correct DLL based on your Python interpreter architecture (x86 or x64).

> [!TIP]
> Example usages for both modules in detail:
> 
> #### Hardware RNG
> Either check out the [example script](example/hwrng_example.py) or the [Wiki page](https://github.com/DefinetlyNotAI/PyCTools/wiki/Py-Documentation-‐-hwrng#methods)
> 
> #### Process Inspection
> Either check out the [example script](example/process_inspect_example.py) or the [Wiki page](https://github.com/DefinetlyNotAI/PyCTools/wiki/Py-Documentation-‐-processInspect#methods)

### DLL Discovery

The Python wrappers automatically search for the correct DLL in:
- `./dist/{arch}/<dll>`
- `../dist/{arch}/<dll>`
- `../../dist/{arch}/<dll>`

where `{arch}` is `x64` or `x86` depending on your Python interpreter.

> More details on how the DLL discovery works can be found in the [Wiki page](https://github.com/DefinetlyNotAI/PyCTools/wiki#dll-discovery-and-dist-directory)

## Extra resources

> [!TIP]
> Want to dive deeper into how everything works? Head over to the [PyCTools Wiki](https://github.com/DefinetlyNotAI/PyCTools/wiki) for detailed breakdowns of the key parts:
>
> • **DLL explanations**: learn how the DLLs are structured, discovered, and loaded 
> • **Python examples, wrappers, and usage**: practical code snippets and usage patterns in Python 
> • **C code explanation**: understand the underlying native implementation
