# Compiler Helper Tool

The project includes a PowerShell script (`tool/compilerHelper.ps1`) to automate building the C source files into DLLs for both x86 and x64 architectures.

## Features
- Detects all `.c` files in the current, `src/`, and `../src/` directories.
- Prompts the user to select which files to compile.
- Cleans up old build artifacts.
- Compiles each selected file for both x86 and x64 using Visual Studio's `cl.exe`.
- Places the resulting DLLs in `dist/x86` and `dist/x64`.
- Handles missing Visual Studio installations by prompting for the path.

## Usage
1. Open PowerShell in the project root.
2. Run:
   ```powershell
   tool\compilerHelper.ps1
   ```
3. For each `.c` file found, answer `Y` to compile or `N` to skip.
4. The script will build and place DLLs in the appropriate `dist/` subfolders.

## Output
- DLLs: `hRng_x64.dll`, `hRng_x86.dll`, `processInspect_x64.dll`, `processInspect_x86.dll`
- Output folders: `dist/x64/`, `dist/x86/`

## Troubleshooting
- If Visual Studio is not detected, you will be prompted to enter the path manually.
- The script requires the Visual Studio C++ build tools to be installed.

# See Also
- [DLL Discovery](https://github.com/DefinetlyNotAI/PyCTools/wiki/DLL-Discovery)

