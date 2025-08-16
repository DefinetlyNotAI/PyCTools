# Python Scripts Documentation: Package Building for PyCTools

---

## Overview

These Python scripts handle the build process for the PyCTools package:

1. `setupHelper.py`: A helper script that:
   - Builds a wheel distribution package
   - Cleans up temporary build files
   - Organizes wheel files into a structured directory
   - Provides guidance for testing and installation

2. `setup.py`: The package configuration file that:
   - Defines package metadata and structure
   - Includes DLLs from bin directory in the package
   - Validates binary files exist before building

> [!IMPORTANT]
> `setup.py` should NOT be run directly at ALL, use `setupHelper.py` only

---

## Prerequisites

* Python 3.9 or higher
* The `build` package installed (`pip install build`)
* The `wheel` package installed (`pip install wheel`)
* The `setuptools` package installed (`pip install setuptools`)
* A properly configured project structure with compiled binaries in the bin folder
* `compilerHelper.ps1` must have been executed previously to create the bin directory

---

## Script Breakdown: setupHelper.py

### Helper Functions

#### `get_version()`
* Extracts the version string from `pyCTools/__init__.py`.
* Returns: The version number of the PyCTools package.
* Exits with error if VERSION string cannot be found or file cannot be read.

#### `success_finale(whl_filename_, version_)`
* Outputs completion messages and instructions for next steps.
* Parameters:
  * `whl_filename_`: Name of the wheel file that was built
  * `version_`: Version of the package
* Prints testing instructions, local installation commands, and GitHub release instructions.

#### `get_latest_wheel(dist_dir, package_name)`
* Finds the most recently modified wheel file matching the package name.
* Parameters:
  * `dist_dir`: Directory to search for wheel files
  * `package_name`: Base name of the package
* Returns: Path to the most recent wheel file.
* Exits if no wheel files are found.

#### `cleanup()`
* Removes build artifacts and organizes wheel files:
  * Removes `./pyCTools.egg-info/` directory
  * Removes `./build/` directory
  * Removes `./pyCTools/dist/` directory
  * Creates `./dist/wheels/` if it doesn't exist
  * Moves wheel files from `./dist/` to `./dist/wheels/`

### Main Script Logic

1. Changes to the parent directory of the script.
2. Runs `python -m build --wheel` as a subprocess to build the wheel package.
3. Cleans up temporary files with `cleanup()`.
4. Gets the path to the latest wheel file.
5. Displays success messages and usage instructions.

---

## Script Breakdown: setup.py

> [!CAUTION]
> Always use `setupHelper.py` or the Python build system (`python -m build`). Direct execution of setup.py is deprecated.

### Helper Functions

#### `check_bin_exists(bin_path)`
* Validates that the bin directory exists with required DLL files.
* Parameters:
  * `bin_path`: Path to the bin directory
* Checks that both x86 and x64 subfolders exist with DLL files.
* Exits with error if validation fails.

#### `output_dir_init()`
* Creates the output directory structure for the wheel.
* Returns: Path to the output directory.
* Exits if directory creation fails.

#### `print_separator(title)`
* Utility function to print a separator line with optional title.

#### `get_version()`
* Extracts version from `pyCTools/__init__.py`.
* Returns: Version string.
* Exits if VERSION string cannot be found or file cannot be read.

### Main Script Logic

1. Extracts version information from `__init__.py`.
2. Validates binary files exist in bin directory.
3. Creates output directory structure.
4. Configures package with metadata and file inclusion rules:
   * Package name, version, author information
   * Includes DLL files from bin/x86 and bin/x64
   * Sets output directories for distribution files

---

## How to Use

### Using setupHelper.py

1. Ensure you've run `compilerHelper.ps1` to create the bin folder with DLL files.

2. Navigate to the `tool` directory in your terminal:
   ```
   cd tool
   ```

3. Run the setupHelper script:
   ```
   python setupHelper.py
   ```

4. The script will:
   - Build a wheel package
   - Clean up build artifacts
   - Organize the wheel file into `dist/wheels/`
   - Provide instructions for testing and installation

5. Follow the displayed instructions to:
   - Test in a virtual environment
   - Install locally
   - Prepare for GitHub release

### About setup.py

* **DO NOT** run setup.py directly! This is deprecated practice.
* The setup.py file should only be used indirectly through:
  - The `setupHelper.py` script (recommended)
  - The Python build system (`python -m build`)
* This file defines the package structure and metadata but is not meant to be executed directly.

---

## Example Output

```
================================================================================
SETUP SCRIPT OUTPUT
================================================================================
...setup output...
================================================================================

[*] Removed ./pyCTools.egg-info/
[*] Removed ./build/
[*] Moved ./dist/pyctools-1.0.0-py3-none-any.whl to ./dist/wheels/pyctools-1.0.0-py3-none-any.whl
[*] Found wheel file successfully

[*] Completed setup.py execution.
        Suggested action: Run 'distributionHelper.ps1' to create the distribution package for github releases.
        Suggested action: Execute the following to test in VENV:
                python -m venv dist/venv_test
                dist\venv_test\Scripts\Activate.ps1
                python -m pip install --upgrade pip
                pip install dist/wheels/pyctools-1.0.0-py3-none-any.whl
                # Do whatever you want here and run any script that uses the library
                deactivate
                Remove-Item -Recurse -Force dist\venv_test

[*] For local installation, run:
        cd ..
        python -m pip install dist/wheels/pyctools-1.0.0-py3-none-any.whl
[*] If you place the WHL file on the GitHub releases page, users can download it and install it with:
        pip install https://github.com/DefinetlyNotAI/PyCTools/releases/download/1.0.0/pyctools-1.0.0-py3-none-any.whl
        > Assuming the version[1.0.0] entered earlier is the exact same as the tag release.
```

---

## Notes

* Always run `compilerHelper.ps1` before building the package to ensure DLL files are available.
* The wheel file is moved to `dist/wheels/` for better organization.
* If multiple wheel files are found, the most recently modified one is selected.
* Setup validation ensures proper directory structure and presence of required files.
* The package includes both x86 and x64 DLL files, making it compatible with both architectures.
* **NEVER** run setup.py directly as this approach is deprecated and may not work correctly.

---

