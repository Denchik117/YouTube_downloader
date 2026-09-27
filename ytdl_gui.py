#!/usr/bin/env python3
"""
ytdl_gui — CustomTkinter GUI for the YouTube video downloader.

Run:
    python3 ytdl_gui.py

Requires: customtkinter, yt-dlp, ffmpeg (for merging and mp3 conversion).
"""

import sys
import threading
import queue
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    raise SystemExit(
        "yt-dlp library not found.\nInstall it: python3 -m pip install -U yt-dlp"
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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def human_size(num_bytes):
    if not num_bytes:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


class VideoOption:
    """Wrapper around a yt-dlp format for display in the dropdown list."""

    def __init__(self, label, format_id, kind):
        self.label = label
        self.format_id = format_id
        self.kind = kind  # "video" or "audio"

    def __str__(self):
        return self.label


def build_video_options(info):
    """List of video qualities: one entry per height, with best audio attached automatically."""
    formats = info.get("formats", [])
    by_height = {}
    for f in formats:
        if f.get("vcodec") == "none":
            continue
        height = f.get("height")
        if not height:
            continue
        fps = f.get("fps") or 0
        ext = f.get("ext", "")
        size = f.get("filesize") or f.get("filesize_approx")
        # for a given height, pick the best by bitrate / larger size
        key = height
        score = (f.get("tbr") or 0)
        if key not in by_height or score > by_height[key][0]:
            by_height[key] = (score, f, fps, ext, size)

    options = []
    for height in sorted(by_height.keys(), reverse=True):
        score, f, fps, ext, size = by_height[height]
        fps_str = f"{fps:.0f}fps " if fps and fps > 30 else ""
        label = f"{height}p {fps_str}({ext}, ~{human_size(size)})"
        # Attach best audio as a separate stream to guarantee sound is present
        format_selector = f'{f["format_id"]}+bestaudio/{f["format_id"]}/best'
        options.append(VideoOption(label, format_selector, "video"))

    if not options:
        options.append(VideoOption("Best available quality", "bestvideo+bestaudio/best", "video"))
    return options


def build_audio_options(info):
    """List of audio tracks (by bitrate); always converted to mp3 on download."""
    formats = info.get("formats", [])
    audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    audio_formats.sort(key=lambda f: f.get("abr") or 0, reverse=True)

    options = []
    seen_abr = set()
    for f in audio_formats:
        abr = round(f.get("abr") or 0)
        if abr in seen_abr:
            continue
        seen_abr.add(abr)
        ext = f.get("ext", "")
        size = f.get("filesize") or f.get("filesize_approx")
        label = f"{abr}kbps ({ext} -> mp3, ~{human_size(size)})"
        options.append(VideoOption(label, f["format_id"], "audio"))

    if not options:
        options.append(VideoOption("Best available audio -> mp3", "bestaudio", "audio"))
    return options


class YtdlGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ytdl - YouTube downloader")
        self.geometry("640x520")
        self.minsize(560, 480)

        self.info = None
        self.video_options = []
        self.audio_options = []
        self.output_dir = str(Path.home() / "Downloads")

        self.msg_queue = queue.Queue()

        self._build_widgets()
        self.after(100, self._poll_queue)

    # ---------- UI ----------

    def _build_widgets(self):
        pad = {"padx": 16, "pady": 8}

        # URL input
        self.url_entry = ctk.CTkEntry(
            self, placeholder_text="Paste the YouTube video link here"
        )
        self.url_entry.pack(fill="x", **pad)

        self.fetch_btn = ctk.CTkButton(
            self, text="Fetch formats", command=self._on_fetch_clicked
        )
        self.fetch_btn.pack(**pad)

        self.title_label = ctk.CTkLabel(self, text="", wraplength=580, justify="left")
        self.title_label.pack(fill="x", **pad)

        # Video/audio mode switch
        self.mode_var = ctk.StringVar(value="video")
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", **pad)
        ctk.CTkRadioButton(
            mode_frame, text="Video (+ audio)", variable=self.mode_var,
            value="video", command=self._refresh_format_list
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            mode_frame, text="Audio only -> mp3", variable=self.mode_var,
            value="audio", command=self._refresh_format_list
        ).pack(side="left")

        # Format list
        self.format_menu = ctk.CTkOptionMenu(self, values=["Fetch formats first"])
        self.format_menu.pack(fill="x", **pad)
        self.format_menu.configure(state="disabled")

        # Output directory
        out_frame = ctk.CTkFrame(self, fg_color="transparent")
        out_frame.pack(fill="x", **pad)
        self.output_label = ctk.CTkLabel(out_frame, text=f"Folder: {self.output_dir}", anchor="w")
        self.output_label.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(out_frame, text="Choose...", width=90, command=self._choose_output_dir).pack(side="right")

        # Download button
        self.download_btn = ctk.CTkButton(
            self, text="Download", command=self._on_download_clicked, state="disabled"
        )
        self.download_btn.pack(**pad)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", **pad)

        self.status_label = ctk.CTkLabel(self, text="Ready.", anchor="w")
        self.status_label.pack(fill="x", **pad)

    # ---------- Actions ----------

    def _choose_output_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.output_dir)
        if chosen:
            self.output_dir = chosen
            self.output_label.configure(text=f"Folder: {self.output_dir}")

    def _on_fetch_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No link", "Paste a video link first.")
            return

        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.download_btn.configure(state="disabled")
        self.format_menu.configure(state="disabled")
        self.status_label.configure(text="Fetching video info...")

        threading.Thread(target=self._fetch_info_worker, args=(url,), daemon=True).start()

    def _fetch_info_worker(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            self.msg_queue.put(("info_ok", info))
        except Exception as e:
            self.msg_queue.put(("info_error", str(e)))

    def _refresh_format_list(self):
        if not self.info:
            return
        options = self.video_options if self.mode_var.get() == "video" else self.audio_options
        labels = [str(o) for o in options]
        self.format_menu.configure(values=labels, state="normal")
        self.format_menu.set(labels[0])

    def _on_download_clicked(self):
        url = self.url_entry.get().strip()
        if not url or not self.info:
            return

        chosen_label = self.format_menu.get()
        options = self.video_options if self.mode_var.get() == "video" else self.audio_options
        chosen = next((o for o in options if str(o) == chosen_label), None)
        if chosen is None:
            messagebox.showerror("Error", "Please select a format.")
            return

        self.download_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Starting download...")

        threading.Thread(
            target=self._download_worker, args=(url, chosen), daemon=True
        ).start()

    def _download_worker(self, url, chosen: VideoOption):
        outtmpl = str(Path(self.output_dir) / "%(title)s [%(id)s].%(ext)s")

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                fraction = downloaded / total if total else 0
                speed = d.get("_speed_str", "").strip()
                self.msg_queue.put(("progress", fraction, speed))
            elif d["status"] == "finished":
                self.msg_queue.put(("processing", None))

        opts = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
        }
        if BUNDLED_FFMPEG:
            opts["ffmpeg_location"] = BUNDLED_FFMPEG

        if chosen.kind == "audio":
            opts["format"] = chosen.format_id
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            opts["format"] = chosen.format_id
            opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.msg_queue.put(("done", None))
        except Exception as e:
            self.msg_queue.put(("download_error", str(e)))

    # ---------- Message queue from background thread ----------

    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _handle_message(self, msg):
        kind = msg[0]

        if kind == "info_ok":
            info = msg[1]
            self.info = info
            self.video_options = build_video_options(info)
            self.audio_options = build_audio_options(info)
            title = info.get("title", "unknown")
            duration = info.get("duration")
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "-"
            self.title_label.configure(text=f"{title}\nDuration: {duration_str}")
            self._refresh_format_list()
            self.fetch_btn.configure(state="normal", text="Fetch formats")
            self.download_btn.configure(state="normal")
            self.status_label.configure(text="Formats fetched. Pick one and click Download.")

        elif kind == "info_error":
            self.fetch_btn.configure(state="normal", text="Fetch formats")
            self.status_label.configure(text="Error fetching info.")
            messagebox.showerror("Error", f"Could not fetch video info:\n{msg[1]}")

        elif kind == "progress":
            fraction, speed = msg[1], msg[2]
            self.progress_bar.set(min(max(fraction, 0), 1))
            self.status_label.configure(text=f"Downloading... {fraction*100:.0f}%  ({speed})")

        elif kind == "processing":
            self.status_label.configure(text="Processing (merging/converting to mp3)...")

        elif kind == "done":
            self.progress_bar.set(1)
            self.status_label.configure(text="Done! File saved.")
            self.download_btn.configure(state="normal")
            self.fetch_btn.configure(state="normal")
            messagebox.showinfo("Done", "Download complete.")

        elif kind == "download_error":
            self.download_btn.configure(state="normal")
            self.fetch_btn.configure(state="normal")
            self.status_label.configure(text="Download error.")
            messagebox.showerror("Error", f"Could not download:\n{msg[1]}")


if __name__ == "__main__":
    app = YtdlGUI()
    app.mainloop()
