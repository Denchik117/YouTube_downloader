# Installs ytdl on Windows.
# Installs Python and ffmpeg via winget (if missing), installs yt-dlp
# and creates the "ytdl" command, available from any PowerShell/cmd window.
#
# Run (from the script's folder, in PowerShell):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\install_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "== Checking winget ==" -ForegroundColor Cyan
if (-not (Test-Command "winget")) {
    Write-Host "winget not found. Install it from the Microsoft Store (App Installer) and run this script again." -ForegroundColor Red
    exit 1
}

Write-Host "== Checking Python ==" -ForegroundColor Cyan
if (-not (Test-Command "python")) {
    Write-Host "Installing Python..."
    winget install -e --id Python.Python.3.12
    Write-Host "Python installed. Restart PowerShell and run this script again so PATH refreshes." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Python is already installed."
}

Write-Host "== Checking ffmpeg (needed for merging video/audio and mp3 conversion) ==" -ForegroundColor Cyan
if (-not (Test-Command "ffmpeg")) {
    Write-Host "Installing ffmpeg..."
    winget install -e --id Gyan.FFmpeg
    Write-Host "ffmpeg installed. Restart PowerShell if the ffmpeg command isn't found." -ForegroundColor Yellow
} else {
    Write-Host "ffmpeg is already installed."
}

Write-Host "== Installing Python dependencies ==" -ForegroundColor Cyan
python -m pip install --user -U -r "$ScriptDir\requirements.txt"

Write-Host "== Creating the 'ytdl' command ==" -ForegroundColor Cyan
$BinDir = "$env:LOCALAPPDATA\ytdl"
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$WrapperPath = "$BinDir\ytdl.bat"
@"
@echo off
python "$ScriptDir\ytdl.py" %*
"@ | Set-Content -Encoding ASCII $WrapperPath

# Add the folder to the user's PATH if it isn't there yet
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "Added $BinDir to PATH." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done! Open a new PowerShell window and run:" -ForegroundColor Green
Write-Host '    ytdl "https://www.youtube.com/watch?v=..."'
Write-Host ""
Write-Host "Examples:"
Write-Host '    ytdl "<link>" -o C:\Users\%USERNAME%\Downloads'
Write-Host '    ytdl "<link>" --best'
Write-Host '    ytdl "<link>" --audio-only'
