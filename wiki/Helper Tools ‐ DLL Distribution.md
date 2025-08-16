# PowerShell Script Documentation: `bin` Folder Validation and ZIP Packaging

---

## Overview

This PowerShell script performs the following tasks:

1. Validates the folder structure and file consistency inside a `bin` directory.
2. Ensures the presence of matching file types and names between `x64` and `x86` subfolders.
3. Verifies DLL naming conventions.
4. Compresses the validated `bin` folder into a ZIP archive in the `dist/rawBinaryZipped` directory.
5. Creates a SHA256 checksum file for the ZIP archive.

---

## Prerequisites

* PowerShell 5.1 or higher (for `Compress-Archive` and `Get-FileHash` cmdlets).
* The script should be run from a directory such that `../pyCTools/bin` refers to your binary folder, or you can input a custom path when prompted.
* The script expects that `compilerHelper.ps1` has been executed previously to create the bin directory.
* Write permission to create a `dist/rawBinaryZipped` folder and to write files inside it.

---

## Script Breakdown

### Global Variables

* `$debug` (Boolean):
  Controls verbose error output. When `$true`, detailed error messages are shown.

### Function: `Write-CustomError`

A helper function to display errors consistently in red.
Parameters:

* `$Message` (string): Main error message to display.
* `$Details` (string, optional): Additional debug info displayed only if `$debug` is `$true`.

---

### Main Script Logic (Inside `try` block)

#### 1. Change Directory

* `Set-Location ..`
  Moves the current working directory one level up.

#### 2. Locate `bin` Folder

* Attempts to find a `bin` folder within the `pyCTools` directory.
* If not found, prompts the user to enter a full path to the `bin` folder, asking if they have executed `compilerHelper.ps1`.
* Exits with error if the path is invalid or missing.

#### 3. Validate Subfolders

* Checks for two mandatory subdirectories inside `bin`:

    * `x64`
    * `x86`
* If either is missing, the script exits with an error.

#### 4. File Type and Count Validation

* Considers the file extensions: `dll`, `exp`, `lib`, and `obj`.
* Retrieves filenames (just names, no paths) for each extension from both `x64` and `x86`.
* Checks if both subfolders have the **same number** of files for each extension.
* If counts differ, it outputs an error showing counts for each folder.

#### 5. File Name Matching

* Extracts the base filename (without extension) for each file.
* For DLL files, removes platform suffixes `_x64` or `_x86` for fair comparison.
* Sorts both sets of base names.
* Checks if the sorted lists match exactly.
* If mismatched, outputs the differing filenames for both folders.

#### 6. DLL Naming Convention Check

* For each DLL file in both folders, checks if the filename contains the folder name (`x64` or `x86`) in any case.
* If a DLL file does **not** contain the folder name, the script throws an error.

#### 7. Success Message

* If all validations pass, it outputs:
  `"bin folder validated successfully."`

---

### Create Output Directory

* Creates a `dist/rawBinaryZipped` directory to store the output files if it doesn't already exist.
* Outputs a message confirming the directory was created or noting that it already exists.

---

### ZIP Compression

* Defines a path for the ZIP file at `dist/rawBinaryZipped/bin.zip`.
* Removes any existing ZIP file with the same name.
* Compresses the entire contents of `bin` into `dist/rawBinaryZipped/bin.zip` using `Compress-Archive`.
* Outputs success or failure message accordingly.

---

### SHA256 Checksum File Creation

* Defines function `SHA256File` which:

    * Computes SHA256 hash of the given file.
    * Creates a `.sha256` file next to the archive.
    * File format:

      ```
      Algorithm : SHA256
      Hash      : <computed_hash>
      ```

* Generates SHA256 checksum for `bin.zip`.

* Outputs confirmation on success or error message on failure.

---

### Error Handling

* Any uncaught exceptions during the script execution are caught.
* Displays a consistent error message using `Write-CustomError`.
* Terminates the script with exit code `1`.

---

## How to Use

1. Place this script somewhere inside your project directory.

2. Ensure you've run `compilerHelper.ps1` to create the `bin` folder structured as follows:

   ```
   bin/
     ├─ x64/
     │    ├─ *.dll, *.exp, *.lib, *.obj files
     └─ x86/
          ├─ *.dll, *.exp, *.lib, *.obj files
   ```

3. The DLL filenames must include `_x64` or `_x86` suffix corresponding to their folder.

4. Run the script from a directory such that moving one directory up (`..`) leads to the location containing the `pyCTools/bin` folder.

5. If no `bin` folder is found, the script will ask you to enter its full path.

6. The script will validate folder structure, file counts, and naming conventions.

7. On successful validation, it will compress `bin` into `dist/rawBinaryZipped/bin.zip` and generate a SHA256 checksum file.

---

## Example Output

```
bin folder validated successfully.
Created rawBinaryZipped folder at C:\Path\To\dist\rawBinaryZipped
ZIP archive created at C:\Path\To\dist\rawBinaryZipped\bin.zip
SHA256 file created: C:\Path\To\dist\rawBinaryZipped\bin.zip.sha256
All done.
```

---

## Notes

* The script assumes you have already compiled your binaries using the `compilerHelper.ps1` script.
* ZIP compression is handled entirely via PowerShell's native `Compress-Archive`.
* The SHA256 format was chosen to be human-readable and simple.
* You can toggle `$debug = $true` at the top to get more detailed error information during development or troubleshooting.

---