param(
    [string]$Source = "cpp\auto_reg_cpp.cpp",
    [string]$Output = "build\auto_reg_cpp.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Source)) {
    throw "Source file not found: $Source"
}

function Refresh-ProcessPath {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $env:Path = "$userPath;$machinePath"
}

$compiler = Get-Command g++ -ErrorAction SilentlyContinue
if (-not $compiler) {
    $compiler = Get-Command cl -ErrorAction SilentlyContinue
}
if (-not $compiler) {
    $compiler = Get-Command clang++ -ErrorAction SilentlyContinue
}

if (-not $compiler) {
    try {
        $packagesPath = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
        $winlibs = Get-ChildItem $packagesPath -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "BrechtSanders.WinLibs.POSIX.UCRT*" } |
            Select-Object -First 1
        if ($winlibs) {
            $gppPath = Join-Path $winlibs.FullName "mingw64\bin\g++.exe"
            if (Test-Path $gppPath -ErrorAction SilentlyContinue) {
                $compiler = [PSCustomObject]@{ Source = $gppPath; Name = "g++.exe" }
            }
        }
    } catch {
        Write-Host "Skipping WinLibs scan: $($_.Exception.Message)"
    }
}

if (-not $compiler) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "No C++ compiler found. Installing WinLibs (g++) via winget..."
        try {
            winget install --id BrechtSanders.WinLibs.POSIX.UCRT --scope user --silent --accept-package-agreements --accept-source-agreements
            Refresh-ProcessPath
        } catch {
            Write-Host "winget installation failed: $($_.Exception.Message)"
        }
    } else {
        Write-Host "winget is not available. Skipping WinLibs installation."
    }

    $compiler = Get-Command g++ -ErrorAction SilentlyContinue
    if (-not $compiler) {
        $compiler = Get-Command cl -ErrorAction SilentlyContinue
    }
    if (-not $compiler) {
        $compiler = Get-Command clang++ -ErrorAction SilentlyContinue
    }
}

if (-not $compiler) {
    throw "No compiler found after installation. Ensure MSVC build tools are initialized or g++ is available."
}

$outDir = Split-Path -Parent $Output
if (-not [string]::IsNullOrWhiteSpace($outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

Write-Host "Using compiler: $($compiler.Source)"
$compilerName = $compiler.Name.ToLowerInvariant()

if ($compilerName -eq "cl.exe") {
    $args = @("/std:c++20", "/O2", "/W4", "/EHsc", $Source, "/Fe:$Output", "winhttp.lib", "gdi32.lib")
    & $compiler.Source @args
    if ($LASTEXITCODE -ne 0) {
        throw "MSVC compilation failed with exit code $LASTEXITCODE"
    }
} else {
    $args = @("-std=c++20", "-O2", "-Wall", "-Wextra")

    if ($compiler.Source -match "mingw" -or $compilerName -eq "g++.exe") {
        $args += @("-static", "-static-libgcc", "-static-libstdc++")
    }

    $args += @($Source, "-o", $Output, "-lwinhttp", "-lgdi32")
    & $compiler.Source @args
    if ($LASTEXITCODE -ne 0) {
        throw "Compilation failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Build done: $Output"
