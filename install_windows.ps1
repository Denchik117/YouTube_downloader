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

Write-Host "== Проверка winget ==" -ForegroundColor Cyan
if (-not (Test-Command "winget")) {
    Write-Host "winget не найден. Установите его из Microsoft Store (App Installer) и запустите скрипт снова." -ForegroundColor Red
    exit 1
}

Write-Host "== Проверка Python ==" -ForegroundColor Cyan
if (-not (Test-Command "python")) {
    Write-Host "Устанавливаю Python..."
    winget install -e --id Python.Python.3.12
    Write-Host "Python установлен. Перезапустите PowerShell и запустите этот скрипт ещё раз, чтобы PATH обновился." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Python уже установлен."
}

Write-Host "== Проверка ffmpeg (нужен для склейки видео/аудио и конвертации в mp3) ==" -ForegroundColor Cyan
if (-not (Test-Command "ffmpeg")) {
    Write-Host "Устанавливаю ffmpeg..."
    winget install -e --id Gyan.FFmpeg
    Write-Host "ffmpeg установлен. Перезапустите PowerShell, если команда ffmpeg не находится." -ForegroundColor Yellow
} else {
    Write-Host "ffmpeg уже установлен."
}

Write-Host "== Установка зависимостей Python ==" -ForegroundColor Cyan
python -m pip install --user -U -r "$ScriptDir\requirements.txt"

Write-Host "== Создание команды 'ytdl' ==" -ForegroundColor Cyan
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
    Write-Host "Папка $BinDir добавлена в PATH." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Готово! Откройте новое окно PowerShell и запускайте:" -ForegroundColor Green
Write-Host '    ytdl "https://www.youtube.com/watch?v=..."'
Write-Host ""
Write-Host "Примеры:"
Write-Host '    ytdl "<ссылка>" -o C:\Users\%USERNAME%\Downloads'
Write-Host '    ytdl "<ссылка>" --best'
Write-Host '    ytdl "<ссылка>" --audio-only'
