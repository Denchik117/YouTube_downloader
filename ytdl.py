#!/usr/bin/env python3
"""
ytdl — command-line downloader for YouTube videos (and other sites supported
by yt-dlp) with format and resolution selection.

Usage:
    python3 ytdl.py <link>
    python3 ytdl.py <link> -o ~/Downloads
    python3 ytdl.py <link> --best          # best quality right away, no prompt
    python3 ytdl.py <link> --audio-only    # audio only right away (mp3)
"""

import argparse
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit(
        "yt-dlp library not found.\n"
        "Install it with:\n"
        "    python3 -m pip install -U yt-dlp"
    )


def get_bundled_ffmpeg():
    """If the app was built by PyInstaller and ffmpeg is bundled inside,
    return its path. Otherwise return None — yt-dlp will look for ffmpeg on PATH."""
    names = ["ffmpeg.exe", "ffmpeg"]
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for name in names:
            candidate = base_dir / name
            if candidate.exists():
                return str(candidate)
    else:
        for name in names:
            candidate = Path(__file__).parent / name
            if candidate.exists():
                return str(candidate)
    return None


BUNDLED_FFMPEG = get_bundled_ffmpeg()


def human_size(num_bytes):
    if not num_bytes:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def list_formats(info):
    """Returns a sorted list of formats with a description for printing."""
    formats = info.get("formats", [])
    rows = []
    for f in formats:
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        has_video = vcodec != "none"
        has_audio = acodec != "none"

        if has_video and has_audio:
            kind = "video+audio"
        elif has_video:
            kind = "video only"
        elif has_audio:
            kind = "audio only"
        else:
            continue

        res = f.get("format_note") or (
            f'{f.get("height")}p' if f.get("height") else ""
        )
        ext = f.get("ext", "")
        fps = f.get("fps")
        size = f.get("filesize") or f.get("filesize_approx")
        abr = f.get("abr")

        desc = f'{f["format_id"]:>8}  {ext:<5} {kind:<12} {res or "":<8}'
        if fps:
            desc += f'{fps:>4}fps '
        else:
            desc += " " * 7
        if abr and not has_video:
            desc += f'{abr:.0f}kbps '
        desc += f'{human_size(size):>8}'

        rows.append((f, desc))

    # Sort: video(+audio) first by descending height, then audio-only
    def sort_key(item):
        f = item[0]
        height = f.get("height") or 0
        has_audio_only = f.get("vcodec") == "none"
        return (has_audio_only, -height)

    rows.sort(key=sort_key)
    return rows


def choose_format_interactively(info):
    rows = list_formats(info)
    if not rows:
        return "best"

    print("\nAvailable formats:\n")
    print(f'{"ID":>8}  {"EXT":<5} {"TYPE":<12} {"RES.":<8}{"":7}{"SIZE":>8}')
    print("-" * 60)
    for _, desc in rows:
        print(desc)
    print("-" * 60)
    print("  best      - best video+audio automatically")
    print("  bestaudio - best audio (can be converted to mp3)")

    choice = input("\nEnter format ID (or 'best' / 'bestaudio'): ").strip()
    return choice or "best"


def build_ydl_opts(output_dir, format_selector, audio_only=False):
    outtmpl = str(Path(output_dir).expanduser() / "%(title)s [%(id)s].%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": False,
        "no_warnings": False,
    }
    if BUNDLED_FFMPEG:
        opts["ffmpeg_location"] = BUNDLED_FFMPEG

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        if format_selector in ("best", ""):
            opts["format"] = "bestvideo+bestaudio/best"
        elif format_selector == "bestaudio":
            opts["format"] = "bestaudio/best"
        else:
            # If a video-only format is selected, add best audio separately
            opts["format"] = f"{format_selector}+bestaudio/{format_selector}/best"
        # Ensure mp4 container where possible (needs ffmpeg for merging)
        opts["merge_output_format"] = "mp4"

    return opts


def progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        sys.stdout.write(f"\r  Downloading: {percent}  speed: {speed}  eta: {eta}   ")
        sys.stdout.flush()
    elif d["status"] == "finished":
        print("\n  Download finished, processing (merge/convert)...")


def main():
    parser = argparse.ArgumentParser(
        description="Download a YouTube video with format and resolution selection."
    )
    parser.add_argument("url", help="Video link")
    parser.add_argument(
        "-o", "--output", default=".", help="Output folder (default: current folder)"
    )
    parser.add_argument(
        "--best", action="store_true", help="Download best quality without prompting"
    )
    parser.add_argument(
        "--audio-only", action="store_true", help="Download audio only (mp3)"
    )
    parser.add_argument(
        "-f", "--format", default=None, help="Format ID directly (skip the prompt)"
    )
    args = parser.parse_args()

    Path(args.output).expanduser().mkdir(parents=True, exist_ok=True)

    print(f"Fetching video info...\n{args.url}\n")

    probe_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(args.url, download=False)
    except yt_dlp.utils.DownloadError as e:
        sys.exit(f"Could not fetch video info: {e}")

    title = info.get("title", "unknown")
    duration = info.get("duration")
    duration_str = (
        f'{duration // 60}:{duration % 60:02d}' if duration else "-"
    )
    print(f'Title: {title}')
    print(f'Duration: {duration_str}')

    if args.audio_only:
        format_selector = "bestaudio"
    elif args.format:
        format_selector = args.format
    elif args.best:
        format_selector = "best"
    else:
        format_selector = choose_format_interactively(info)

    ydl_opts = build_ydl_opts(args.output, format_selector, audio_only=args.audio_only)

    print(f'\nStarting download into: {Path(args.output).expanduser().resolve()}\n')
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([args.url])
    except yt_dlp.utils.DownloadError as e:
        sys.exit(f"\nDownload error: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
