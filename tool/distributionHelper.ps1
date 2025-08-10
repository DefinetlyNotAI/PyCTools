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

try {
    # Move one directory up
    Set-Location ..

    $binPath = Join-Path (Join-Path (Get-Location) "pyCTools") "bin"

    if (-not (Test-Path $binPath -PathType Container)) {
        $binPath = Read-Host "bin folder not found. [Have you executed 'compilerHelper.ps1'?] => Please enter the full path to the bin folder"
        if (-not (Test-Path $binPath -PathType Container)) {
            Write-CustomError "Provided bin path does not exist or is not a directory."
            exit 1
        }
    }

    # Validate bin structure
    $x64Path = Join-Path $binPath "x64"
    $x86Path = Join-Path $binPath "x86"

    if (-not (Test-Path $x64Path -PathType Container)) {
        Write-CustomError "x64 folder is missing inside bin."
        exit 1
    }
    if (-not (Test-Path $x86Path -PathType Container)) {
        Write-CustomError "x86 folder is missing inside bin."
        exit 1
    }

    $types = @("dll", "exp", "lib", "obj")

    $x64Files = @{}
    $x86Files = @{}

    foreach ($ext in $types) {
        $x64Files[$ext] = Get-ChildItem -Path $x64Path -Filter "*.$ext" -File | Select-Object -ExpandProperty Name
        $x86Files[$ext] = Get-ChildItem -Path $x86Path -Filter "*.$ext" -File | Select-Object -ExpandProperty Name
    }

    foreach ($ext in $types) {
        if ($x64Files[$ext].Count -ne $x86Files[$ext].Count) {
            Write-CustomError "Mismatch in number of *.$ext files between x64 and x86 folders."
            Write-Host "  - x64 count: $($x64Files[$ext].Count), x86 count: $($x86Files[$ext].Count)" -ForegroundColor Red
            exit 1
        }
    }

    foreach ($ext in $types) {
        $x64BaseNames = $x64Files[$ext] | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) }
        $x86BaseNames = $x86Files[$ext] | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_) }

        if ($ext -eq "dll") {
            $x64BaseNames = $x64BaseNames | ForEach-Object { $_ -replace "_x64$", "" }
            $x86BaseNames = $x86BaseNames | ForEach-Object { $_ -replace "_x86$", "" }
        }

        $x64BaseNames = $x64BaseNames | Sort-Object
        $x86BaseNames = $x86BaseNames | Sort-Object

        if (($x64BaseNames -join ',') -ne ($x86BaseNames -join ',')) {
            Write-CustomError "Filenames mismatch in *.$ext files between x64 and x86 folders."
            Write-Host "  - x64: $($x64BaseNames -join ', ')" -ForegroundColor Red
            Write-Host "  - x86: $($x86BaseNames -join ', ')" -ForegroundColor Red
            exit 1
        }
    }

    foreach ($folderInfo in @(@{Path=$x64Path; Name="x64"}, @{Path=$x86Path; Name="x86"})) {
        $dllFiles = Get-ChildItem -Path $folderInfo.Path -Filter "*.dll" -File
        foreach ($dll in $dllFiles) {
            if (-not $dll.Name.ToLower().Contains($folderInfo.Name.ToLower())) {
                Write-CustomError "DLL file '$($dll.Name)' in folder '$($folderInfo.Name)' does NOT contain the folder name."
                exit 1
            }
        }
    }

    Write-Host "bin folder validated successfully."

    # Create dist folder if not exists
    $distPath = Join-Path (Split-Path (Split-Path $binPath -Parent) -Parent) "dist"
    if (-not (Test-Path $distPath)) {
        New-Item -Path $distPath -ItemType Directory -ErrorAction Stop | Out-Null
        Write-Host "Created dist folder at $distPath"
    } else {
        Write-Host "dist folder already exists at $distPath"
    }

    # Compress bin folder to ZIP
    $zipFile = Join-Path $distPath "bin.zip"

    if (Test-Path $zipFile) { Remove-Item $zipFile -Force }
    try {
        Compress-Archive -Path (Join-Path $binPath '*') -DestinationPath $zipFile -Force
        Write-Host "ZIP archive created at $zipFile"
    }
    catch {
        Write-CustomError "Failed to create ZIP archive." $_.Exception.Message
        exit 1
    }

    # Create SHA256 file for ZIP archive
    function SHA256File {
        param(
            [string]$filePath
        )
        try {
            $hashObj = Get-FileHash -Algorithm SHA256 -Path $filePath
            $shaFile = "$filePath.sha256"
            $content = @"
Algorithm : SHA256
Hash      : $($hashObj.Hash)
"@
            Set-Content -Path $shaFile -Value $content -Encoding UTF8
            Write-Host "SHA256 file created: $shaFile"
        }
        catch {
            Write-CustomError "Failed to create SHA256 file for $filePath." $_.Exception.Message
            exit 1
        }
    }

    SHA256File -filePath $zipFile

    Write-Host "All done."

} catch {
    Write-CustomError "Unexpected error occurred." $_.Exception.Message
    exit 1
}
