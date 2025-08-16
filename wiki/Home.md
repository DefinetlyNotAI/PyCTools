# Welcome to the PyCTools Wiki

**PyCTools** is a lightweight set of native DLLs and Python bindings for process inspection, memory analysis, and system metric collection on Windows.

This wiki serves as the official documentation hub. Whether you're a C developer building your own DLLs, a Python user leveraging the wrappers, or just curious how the system works under the hood — you're in the right place.

### What You'll Find Here:

* **DLL Internals & Discovery**
  How the `processInspect` and `hRng` DLLs are structured, built, and dynamically located.

* **Python Usage & Examples**
  Step-by-step guides for using the wrapper classes, session handling, and metric querying.

* **C Code Explanations**
  Detailed look into the native code powering the DLLs, from memory APIs to performance counters.

> ⚙ Whether you're downloading prebuilt binaries or compiling from source — this wiki will help you understand how it all fits together.

---

# DLL Discovery and `bin/` Directory

> [!IMPORTANT]
> Starting from `v0.2.0-beta` the script now purely checks `bin/` inside the `pyCTools` directory!
>
> In short ignore everything on the bottom

## DLL Output Structure

Compiled DLLs are placed in the `bin/` directory, organized by architecture:

```
dist/
  x64/
    hRng_x64.dll
    processInspect_x64.dll
    ...
  x86/
    hRng_x86.dll
    processInspect_x86.dll
    ...
```

- `x64/`: DLLs for 64-bit Python and applications
- `x86/`: DLLs for 32-bit Python and applications

## How Python Finds the DLLs

Both `hwrng` and `processInspect` automatically search for the correct DLL based on your Python interpreter's architecture. Locations that are searched are:

- `./bin/{arch}/{dll}_{arch}.dll` (relative to the Python library file)

> Where `{arch}` is `x64` or `x86` and `{dll}` is the mentioned/provided dll per library.

> If the DLL is not found, a `FileNotFoundError` is raised.

## Building the DLLs 

1. Open **PowerShell** and run:
   ```powershell
   cd ./tool/
   compilerHelper.ps1
   ```
   
2. Choose the `.c` source files you want to compile.

3. The script will compile for **both x86 and x64** architectures, placing the output in:
   - `pyCTools/bin/x86` (32-bit builds)
   - `pyCTools/bin/x64` (64-bit builds)

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

## Troubleshooting
- If you get DLL not found errors, check that the correct DLLs exist in the expected `bin/{arch}` folders.
- Ensure you are using the correct Python architecture (x64 or x86) for the DLLs present.

