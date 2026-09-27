#!/usr/bin/env bash
# Installs ytdl on macOS.
# Installs Homebrew packages (python, ffmpeg) if needed and dependencies from requirements.txt,
# then places the "ytdl" command in /usr/local/bin (or /opt/homebrew/bin on Apple Silicon).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Проверка Homebrew =="
if ! command -v brew &> /dev/null; then
    echo "Homebrew не найден. Установите его: https://brew.sh"
    exit 1
fi

echo "== Проверка ffmpeg (нужен для склейки видео/аудио и конвертации в mp3) =="
if ! command -v ffmpeg &> /dev/null; then
    echo "Устанавливаю ffmpeg..."
    brew install ffmpeg
else
    echo "ffmpeg уже установлен."
fi

echo "== Проверка python3 =="
if ! command -v python3 &> /dev/null; then
    echo "Устанавливаю python3..."
    brew install python
else
    echo "python3 уже установлен."
fi

echo "== Установка зависимостей Python =="
python3 -m pip install --user -U -r "$SCRIPT_DIR/requirements.txt"

echo "== Создание команды 'ytdl' =="
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
echo "Готово! Теперь можно запускать из любой папки терминала:"
echo "    ytdl https://www.youtube.com/watch?v=..."
echo ""
echo "Примеры:"
echo "    ytdl <ссылка> -o ~/Downloads"
echo "    ytdl <ссылка> --best"
echo "    ytdl <ссылка> --audio-only"
