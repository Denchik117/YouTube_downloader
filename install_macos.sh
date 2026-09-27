#!/usr/bin/env bash
# Installs ytdl on macOS.
# Installs Homebrew packages (python, ffmpeg) if needed and dependencies from
# requirements.txt, then places the "ytdl" command in /usr/local/bin (or
# /opt/homebrew/bin on Apple Silicon).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Checking Homebrew =="
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Install it: https://brew.sh"
    exit 1
fi

echo "== Checking ffmpeg (needed for merging video/audio and mp3 conversion) =="
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing ffmpeg..."
    brew install ffmpeg
else
    echo "ffmpeg is already installed."
fi

echo "== Checking python3 =="
if ! command -v python3 &> /dev/null; then
    echo "Installing python3..."
    brew install python
else
    echo "python3 is already installed."
fi

echo "== Installing Python dependencies =="
python3 -m pip install --user -U -r "$SCRIPT_DIR/requirements.txt"

echo "== Creating the 'ytdl' command =="
BIN_DIR="/usr/local/bin"
if [ -d "/opt/homebrew/bin" ]; then
    BIN_DIR="/opt/homebrew/bin"
fi

WRAPPER="$BIN_DIR/ytdl"
cat > /tmp/ytdl_wrapper <<EOF
#!/usr/bin/env bash
exec python3 "$SCRIPT_DIR/ytdl.py" "\$@"
EOF
chmod +x /tmp/ytdl_wrapper

if [ -w "$BIN_DIR" ]; then
    mv /tmp/ytdl_wrapper "$WRAPPER"
else
    sudo mv /tmp/ytdl_wrapper "$WRAPPER"
fi
chmod +x "$WRAPPER"

echo ""
echo "Done! You can now run this from any terminal window:"
echo "    ytdl https://www.youtube.com/watch?v=..."
echo ""
echo "Examples:"
echo "    ytdl <link> -o ~/Downloads"
echo "    ytdl <link> --best"
echo "    ytdl <link> --audio-only"
