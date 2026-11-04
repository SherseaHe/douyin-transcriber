import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

AUDIO_EXTENSIONS = {".mp3": "mp3", ".wav": "wav", ".ogg": "ogg"}

def run(command, cwd=None):
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stdout}")
    return result.stdout


def require_binary(name, install_hint):
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Missing {name}. {install_hint}")
    return path


def public_audio_format(url):
    path = urlparse(url).path.lower()
    for extension, audio_format in AUDIO_EXTENSIONS.items():
        if path.endswith(extension):
            return audio_format
    return ""


def download_video(url, work_dir, cookies_from_browser):
    require_binary("yt-dlp", "Install it with: brew install yt-dlp")
    work_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(work_dir / "%(id)s.%(ext)s")
    command = [
        "yt-dlp",
        "--no-playlist",
        "--print", "after_move:filepath",
        "-f",
        "bv*+ba/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        url,
    ]
    if cookies_from_browser:
        command[1:1] = ["--cookies-from-browser", cookies_from_browser]
    output = run(command)
    for line in reversed(output.splitlines()):
        candidate = Path(line.strip())
        if candidate.is_file() and candidate.resolve().parent == work_dir.resolve():
            return candidate
    raise RuntimeError("yt-dlp finished but did not report a completed media file.")


def extract_audio(input_path, work_dir):
    require_binary("ffmpeg", "Install it with: brew install ffmpeg")
    audio_path = work_dir / "audio.mp3"
    run([
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        str(audio_path),
    ])
    return audio_path
