@echo off
REM Builds ytdl_gui.exe with ffmpeg.exe bundled inside - run this once on
REM Windows; the resulting .exe can then be copied and run with a double
REM click on any Windows machine without Python, PowerShell, or a separate
REM ffmpeg install.
REM
REM Usage: double-click this file from the folder containing ytdl_gui.py.

setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install it first: winget install -e --id Python.Python.3.12
    pause
    exit /b 1
)

echo == Installing dependencies ==
python -m pip install --user -U -r requirements.txt pyinstaller

REM --- Download ffmpeg.exe if it isn't already sitting here ---
if not exist ffmpeg.exe (
    echo == ffmpeg.exe not found, downloading ==
    if not exist ffmpeg_tmp mkdir ffmpeg_tmp
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg_tmp\ffmpeg.zip'"
    if errorlevel 1 (
        echo Could not download ffmpeg automatically.
        echo Download it manually from https://www.gyan.dev/ffmpeg/builds/, find
        echo bin\ffmpeg.exe inside the archive, and place it in this folder
        echo next to build_exe.bat as ffmpeg.exe, then run this script again.
        pause
        exit /b 1
    )
    powershell -NoProfile -Command ^
        "Expand-Archive -Path 'ffmpeg_tmp\ffmpeg.zip' -DestinationPath 'ffmpeg_tmp' -Force"
    for /r ffmpeg_tmp %%f in (ffmpeg.exe) do copy /Y "%%f" ffmpeg.exe >nul
    rmdir /s /q ffmpeg_tmp
    if not exist ffmpeg.exe (
        echo Could not find ffmpeg.exe inside the downloaded archive.
        echo Please add it manually and try again.
        pause
        exit /b 1
    )
    echo ffmpeg.exe ready.
) else (
    echo ffmpeg.exe already present, using it.
)

echo == Building ytdl_gui.exe (this may take a couple of minutes) ==
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name ytdl_gui ^
    --collect-all customtkinter ^
    --add-binary "ffmpeg.exe;." ^
    ytdl_gui.py

echo.
if exist dist\ytdl_gui.exe (
    copy /Y dist\ytdl_gui.exe ytdl_gui.exe >nul
    echo Done! ytdl_gui.exe was created in this folder, with ffmpeg bundled inside.
    echo You can copy it to any Windows computer and run it with a double
    echo click - no Python, no ffmpeg install needed.
) else (
    echo Something went wrong, the build did not produce ytdl_gui.exe. Check the output above.
)

pause
