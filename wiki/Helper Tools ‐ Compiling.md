# Compiler Helper Tool

The project includes a PowerShell script (`tool/compilerHelper.ps1`) to automate building the C source files into DLLs for both x86 and x64 architectures.

## Features
- Automatically looks for `.c` files in the `../src/` directory
- Prompts the user to select which files to compile (with interactive selection)
- Supports command-line arguments for batch processing
- Cleans up old build artifacts
- Compiles each selected file for both x86 and x64 using Visual Studio's `cl.exe`
- Places the resulting DLLs in `pyCTools/bin/x86` and `pyCTools/bin/x64`
- Automatically detects Visual Studio installation paths
- Handles missing Visual Studio installations by prompting for the path

## Usage

### Basic Usage
1. Open PowerShell in the project root or tool directory
2. Run:
   ```powershell
   tool\compilerHelper.ps1
   ```
3. For each `.c` file found, answer `Y` to compile or `N` to skip
4. The script will build and place DLLs in the appropriate output folders

### Advanced Usage

#### Automatic Acceptance
To compile all found files without prompting:
```powershell
tool\compilerHelper.ps1 -y
```

#### Specific Files
To compile only specific files:
```powershell
tool\compilerHelper.ps1 file1.c file2.c
```

## Output
- DLL naming: `[filename]_[architecture].dll` (e.g., `hRng_x64.dll`, `hRng_x86.dll`)
- Output folders: `../bin/x64/` and `../bin/x86/`
- Build artifacts (.obj, .lib, .exp files) are also placed in the output folders

## Troubleshooting
- If Visual Studio is not detected automatically, you will be prompted to enter the path manually
- The script requires the Visual Studio C++ build tools to be installed
- Set `$debug = $true` at the top of the script to see more detailed error messages

# See Also
- [DLL Discovery](https://github.com/DefinetlyNotAI/PyCTools/wiki/DLL-Discovery)

