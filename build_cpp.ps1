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

$compiler = Get-Command clang++ -ErrorAction SilentlyContinue
if (-not $compiler) {
    $compiler = Get-Command g++ -ErrorAction SilentlyContinue
}

if (-not $compiler) {
    $winlibs = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "BrechtSanders.WinLibs.POSIX.UCRT*" } |
        Select-Object -First 1
    if ($winlibs) {
        $gppPath = Join-Path $winlibs.FullName "mingw64\bin\g++.exe"
        if (Test-Path $gppPath) {
            $compiler = [PSCustomObject]@{ Source = $gppPath; Name = "g++.exe" }
        }
    }
}

if (-not $compiler) {
    Write-Host "No C++ compiler found. Installing WinLibs (g++) via winget..."
    winget install --id BrechtSanders.WinLibs.POSIX.UCRT --scope user --silent --accept-package-agreements --accept-source-agreements
    Refresh-ProcessPath
    $compiler = Get-Command clang++ -ErrorAction SilentlyContinue
    if (-not $compiler) {
        $compiler = Get-Command g++ -ErrorAction SilentlyContinue
    }
}

if (-not $compiler) {
    throw "No compiler found after installation."
}

$outDir = Split-Path -Parent $Output
if (-not [string]::IsNullOrWhiteSpace($outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

Write-Host "Using compiler: $($compiler.Source)"
$args = @("-std=c++20", "-O2", "-Wall", "-Wextra")

if ($compiler.Source -match "mingw" -or $compiler.Name -eq "g++.exe") {
    $args += @("-static", "-static-libgcc", "-static-libstdc++")
}

$args += @($Source, "-o", $Output, "-lwinhttp")
& $compiler.Source @args

Write-Host "Build done: $Output"
