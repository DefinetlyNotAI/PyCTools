# PowerShell script: DLL Builder

$debug = $false

function Write-CustomError {
    param(
        [string]$Message,
        [string]$Details = ""
    )
    Write-Host $Message -ForegroundColor Red
    if ($debug -and $Details) {
        Write-Host $Details -ForegroundColor DarkRed
    }
}

# Get .c files in current directory, ../src, or ./src
$cFiles = @()
foreach ($dir in @(".", "..\src", ".\src")) {
    if (Test-Path $dir) {
        $cFiles += Get-ChildItem -Path $dir -Filter *.c -File | ForEach-Object { $_.FullName }
    }
}
if (-not $cFiles) {
    Write-CustomError "No .c files found in current directory. Exiting."
    exit 1
}

# Handle -y and file arguments for auto-accept and selection
$acceptAll = $false
$specifiedFiles = @()
foreach ($arg in $args) {
    if ($arg -eq "-y") {
        $acceptAll = $true
    } elseif ($arg -like "*.c") {
        $specifiedFiles += $arg
    }
}

$filesToCompile = @()
if ($specifiedFiles.Count -gt 0) {
    foreach ($file in $specifiedFiles) {
        if ($cFiles -contains $file) {
            $filesToCompile += $file
        } else {
            Write-CustomError "Specified file not found: $file"
        }
    }
} elseif ($acceptAll) {
    $filesToCompile = $cFiles
} else {
    foreach ($file in $cFiles) {
        $answer = Read-Host "Compile '$file'? (Y/N, default N)"
        if ($answer -match '^(y|Y)$') {
            $filesToCompile += $file
        }
    }
}

if ($filesToCompile.Count -eq 0) {
    Write-CustomError "No files selected for compilation. Exiting."
    exit 1
}

# --- CLEANUP: Remove .obj/.dll/.lib/.exp in root and move all outputs to bin/{arch} ---
$binRoot = "..\pyCTools\bin"
$x64Folder = Join-Path $binRoot "x64"
$x86Folder = Join-Path $binRoot "x86"

# Create output folders
foreach ($folder in @($binRoot, $x64Folder, $x86Folder)) {
    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder | Out-Null
        Write-Host "Created folder: $folder"
    }
    else {
        Write-Host "Folder already exists: $folder"
    }
}

# Remove build artifacts from root (not in bin)
$extensionsToClean = @("*.obj", "*.dll", "*.lib", "*.exp")
foreach ($ext in $extensionsToClean) {
    Get-ChildItem -Path . -Filter $ext -File | Remove-Item -Force -ErrorAction SilentlyContinue
}

function Get-VSPath {
    # Search for Visual Studio's vcvarsall.bat in common locations
    $searchPaths = @(
    # Standard VS install locations
        "$env:ProgramFiles\Microsoft Visual Studio",
        "$env:ProgramFiles(x86)\Microsoft Visual Studio",
        # Known VS2019 BuildTools path
        "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools",
        # Start Menu shortcut location (user request)
        "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Studio 2019\Visual Studio Tools\VC"
    )

    foreach ($root in $searchPaths) {
        if (Test-Path $root) {
            # If the root is a direct VC tools folder, check for vcvarsall.bat directly
            $vcvarsDirect = Join-Path $root "vcvarsall.bat"
            if (Test-Path $vcvarsDirect) {
                return $root
            }
            # Otherwise, search subfolders for vcvarsall.bat (limit depth for performance)
            $foundVcvars = Get-ChildItem -Path $root -Filter "vcvarsall.bat" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($foundVcvars) {
                # Return the parent directory containing vcvarsall.bat
                return Split-Path $foundVcvars.FullName -Parent
            }
        }
    }
    return $null
}

# Function to run VS developer cmd and compile for target arch
function CompileDll {
    param(
        [string]$Arch, # x86 or x64
        [string]$OutFolder,
        [string]$File
    )

    $vsPath = Get-VSPath
    if (-not $vsPath) {
        $vsPath = Read-Host "Could not auto-detect Visual Studio path. Please enter the path to your VS installation (e.g. C:\Program Files (x86)\Microsoft Visual Studio\2019\Community)"
        if (-not (Test-Path $vsPath)) {
            Write-CustomError "Provided Visual Studio path does not exist: $vsPath"
            return $false
        }
    }

    # Try to find vcvarsall.bat in the provided path or its subfolders
    $vcvarsPath = Join-Path $vsPath "VC\Auxiliary\Build\vcvarsall.bat"
    if (-not (Test-Path $vcvarsPath)) {
        # Try direct path (if user gave path to VC tools folder)
        $vcvarsPath = Join-Path $vsPath "vcvarsall.bat"
        if (-not (Test-Path $vcvarsPath)) {
            # Try searching subfolders
            $foundVcvars = Get-ChildItem -Path $vsPath -Filter "vcvarsall.bat" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($foundVcvars) {
                $vcvarsPath = $foundVcvars.FullName
            } else {
                Write-CustomError "vcvarsall.bat not found at $vcvarsPath"
                return $false
            }
        }
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($File)
    $dllName = "${baseName}_${Arch}.dll"
    $dllPath = Join-Path $OutFolder $dllName

    # Output files for cleanup/move
    $objName = "${baseName}.obj"
    $libName = "${baseName}.lib"
    $expName = "${baseName}.exp"

    $cmd = @"
call `"$vcvarsPath`" $Arch
cl /LD $File /Fo`"$objName`" /link /out:`"$dllPath`"
exit /b %errorlevel%
"@

    Write-Host "Compiling $File for $Arch..."
    $tempFile = [System.IO.Path]::GetTempFileName() + ".bat"
    Set-Content -Path $tempFile -Value $cmd -Encoding ASCII

    try {
        $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$tempFile`"" -NoNewWindow -Wait -PassThru
        Remove-Item $tempFile -Force
        if ($proc.ExitCode -ne 0) {
            Write-CustomError "Compilation failed for $File ($Arch)." "Exit code: $($proc.ExitCode)"
            return $false
        }
    } catch {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        Write-CustomError "Compilation process failed for $File ($Arch)." $_.Exception.Message
        return $false
    }

    # Move .obj, .lib, .exp to output folder if they exist
    foreach ($artifact in @($objName, $libName, $expName)) {
        if (Test-Path $artifact) {
            Move-Item $artifact $OutFolder -Force
        }
    }

    Write-Host "Compilation succeeded for $File ($Arch). Output: $dllPath"
    return $true
}

# Compile each file as its own DLL for x64 and x86, outputs in bin/x64 and bin/x86
foreach ($file in $filesToCompile) {
    if (-not (CompileDll -Arch "x64" -OutFolder $x64Folder -File $file)) {
        Write-CustomError "x64 build failed for $file."
    }
    if (-not (CompileDll -Arch "x86" -OutFolder $x86Folder -File $file)) {
        Write-CustomError "x86 build failed for $file."
    }
}

Write-Host "Build process completed."
