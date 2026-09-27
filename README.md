# ytdl — YouTube video downloader

A command-line tool and a graphical interface (CustomTkinter) for downloading
YouTube videos with resolution selection, plus audio with automatic
conversion to mp3. Built on top of the `yt-dlp` library.

## Folder contents

| File                  | Purpose                                                     |
|-----------------------|--------------------------------------------------------------|
| `ytdl.py`             | Command-line version                                        |
| `ytdl_gui.py`         | Graphical version (CustomTkinter)                            |
| `requirements.txt`    | Python dependencies (`yt-dlp`, `customtkinter`)               |
| `install_macos.sh`    | macOS installer (ffmpeg, python, dependencies, PATH)          |
| `install_windows.ps1` | Windows installer (ffmpeg, python, dependencies, PATH)        |
| `build_exe.bat`       | Builds a standalone `ytdl_gui.exe` on Windows (see below)     |

## Quick install

### macOS

1. Open Terminal in this folder.
2. Run:
   ```bash
   chmod +x install_macos.sh
   ./install_macos.sh
   ```
3. The installer will set up `ffmpeg` and `python3` via Homebrew (if
   missing) and add the `ytdl` command to your PATH.

### Windows

1. Open PowerShell in this folder.
2. Run:
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\install_windows.ps1
   ```
3. The installer will set up Python and ffmpeg via `winget` (if missing) and
   add the `ytdl` command to your user PATH. If Python/ffmpeg was just
   installed, close and reopen PowerShell, then run the script again.

### Windows — no PowerShell, no commands: a standalone .exe with bundled ffmpeg

If you'd rather not open PowerShell or install ffmpeg separately at all:

1. Once (you or whoever hands the program over) — double-click
   `build_exe.bat` from the folder containing `ytdl_gui.py`. It will:
   - install `pyinstaller`,
   - download `ffmpeg.exe` if it isn't already there,
   - build `ytdl_gui.exe` **with ffmpeg bundled inside**.
2. From then on, `ytdl_gui.exe` is a self-contained program: copy it to any
   Windows computer and run it with a double click. No Python, no
   PowerShell, no separate ffmpeg install needed at all.

Building the `.exe` only works on Windows itself (PyInstaller can't
cross-compile a Windows exe from Linux/macOS), so `build_exe.bat` must be
run on a Windows machine — but only once; the resulting `.exe` can then be
freely copied and shared without Python or ffmpeg.

If the automatic ffmpeg download fails (no internet, blocked site, etc.),
the script will tell you where to download `ffmpeg.exe` manually and where
to place it, then just run `build_exe.bat` again.

### Manual install (any OS)

```bash
pip install -r requirements.txt
```

Plus install `ffmpeg` separately (needed for merging video+audio and mp3
conversion):
- macOS: `brew install ffmpeg`
- Windows: `winget install -e --id Gyan.FFmpeg`

## Usage

### Graphical interface

```bash
python3 ytdl_gui.py      # macOS/Linux
python ytdl_gui.py       # Windows
```

1. Paste the video link into the input field.
2. Click "Fetch formats".
3. Choose a mode: "Video (+ audio)" or "Audio only -> mp3".
4. Pick the desired resolution/bitrate from the dropdown.
5. Optionally change the save folder with the "Choose..." button.
6. Click "Download".

For video, the best available audio is always attached automatically to
the chosen resolution. For audio, whatever bitrate you pick is converted to
**mp3** via ffmpeg.

### Command line

```bash
ytdl "<link>"                  # interactive format selection
ytdl "<link>" -o ~/Downloads   # save to a specific folder
ytdl "<link>" --best           # best quality right away, no prompt
ytdl "<link>" --audio-only     # audio only right away -> mp3
ytdl "<link>" -f 137           # download a specific format ID directly
```

If the `ytdl` command isn't found, run the script directly:
`python3 ytdl.py "<link>"` (or `python` on Windows).

**Important:** always wrap the link in quotes — otherwise characters like
`&`, `?`, `=` may be misinterpreted by the shell (especially in zsh on
macOS).

## Requirements

- Python 3.8+
- ffmpeg (merging video/audio, mp3 conversion)
- `yt-dlp`, `customtkinter` (installed automatically by the install scripts,
  or manually via `requirements.txt`)

## Troubleshooting

- **`zsh: no matches found: https://...`** — the link isn't quoted, see
  above.
- **Error while merging video and audio** — ffmpeg isn't installed or isn't
  on PATH; reinstall via the install script or manually.
- **`winget` not found (Windows)** — install "App Installer" from the
  Microsoft Store, then run `install_windows.ps1` again.
- **Homebrew not found (macOS)** — install it from https://brew.sh, then
  run `install_macos.sh` again.
