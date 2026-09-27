@echo off
REM Builds ytdl_gui.exe with ffmpeg.exe bundled inside — run this once on
REM Windows; the resulting .exe can then be copied and run with a double
REM click on any Windows machine without Python, PowerShell, or a separate
REM ffmpeg install.
REM
REM Usage: double-click this file from the folder containing ytdl_gui.py.

setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo Python не найден. Сначала установите его: winget install -e --id Python.Python.3.12
    pause
    exit /b 1
)

echo == Установка зависимостей ==
python -m pip install --user -U -r requirements.txt pyinstaller

REM --- Download ffmpeg.exe if it isn't already sitting here ---
if not exist ffmpeg.exe (
    echo == ffmpeg.exe не найден, скачиваю ==
    if not exist ffmpeg_tmp mkdir ffmpeg_tmp
    powershell -NoProfile -Command ^
        "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg_tmp\ffmpeg.zip'"
    if errorlevel 1 (
        echo Не удалось скачать ffmpeg автоматически.
        echo Скачайте вручную с https://www.gyan.dev/ffmpeg/builds/, найдите
        echo файл bin\ffmpeg.exe внутри архива и положите его в эту папку
        echo рядом с build_exe.bat под именем ffmpeg.exe, затем запустите
        echo этот скрипт снова.
        pause
        exit /b 1
    )
    powershell -NoProfile -Command ^
        "Expand-Archive -Path 'ffmpeg_tmp\ffmpeg.zip' -DestinationPath 'ffmpeg_tmp' -Force"
    for /r ffmpeg_tmp %%f in (ffmpeg.exe) do copy /Y "%%f" ffmpeg.exe >nul
    rmdir /s /q ffmpeg_tmp
    if not exist ffmpeg.exe (
        echo Не удалось найти ffmpeg.exe в скачанном архиве. Соберите вручную
        echo и повторите попытку.
        pause
        exit /b 1
    )
    echo ffmpeg.exe готов.
) else (
    echo ffmpeg.exe уже есть рядом, использую его.
)

echo == Сборка ytdl_gui.exe (это может занять пару минут) ==
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name ytdl_gui ^
    --collect-all customtkinter ^
    --add-binary "ffmpeg.exe;." ^
    ytdl_gui.py

echo.
if exist dist\ytdl_gui.exe (
    copy /Y dist\ytdl_gui.exe ytdl_gui.exe >nul
    echo Готово! Файл ytdl_gui.exe создан в этой папке, ffmpeg встроен внутрь.
    echo Программу можно скопировать на любой Windows-компьютер и запускать
    echo двойным кликом — ни Python, ни ffmpeg отдельно ставить не нужно.
) else (
    echo Что-то пошло не так, сборка не создала ytdl_gui.exe. Проверьте вывод выше.
)

pause
