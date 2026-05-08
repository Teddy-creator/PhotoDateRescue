param(
    [string]$AppName = "PhotoDateRescue",
    [string]$VenvDir = ".venv-windows-gui"
)

$ErrorActionPreference = "Stop"

$IsRunningOnWindows = [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
    [System.Runtime.InteropServices.OSPlatform]::Windows
)
if (-not $IsRunningOnWindows) {
    Write-Error "Windows exe packaging must run on Windows."
}

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RootDir

Write-Host "Creating build environment: $VenvDir"
python -m venv $VenvDir
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade pip
& "$VenvDir\Scripts\python.exe" -m pip install -e ".[dev]" pyinstaller

Write-Host "Cleaning old build artifacts"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Force "$AppName.spec" -ErrorAction SilentlyContinue

Write-Host "Building $AppName.exe"
& "$VenvDir\Scripts\python.exe" -m PyInstaller `
    --windowed `
    --name $AppName `
    src\photodaterescue\gui_launcher.py

Write-Host ""
Write-Host "Built: $RootDir\dist\$AppName\$AppName.exe"
Write-Host "Note: ExifTool is required at runtime and is not bundled."
