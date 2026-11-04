#!/usr/bin/env python3
import argparse
import hashlib
import tempfile
import fcntl
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import doubao_flash_asr
import douyin_resolver
from media import AUDIO_EXTENSIONS, download_video, extract_audio, public_audio_format
from asr_common import write_transcript_outputs as write_outputs


MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1"
)


def now():
    return time.perf_counter()


def elapsed_since(start):
    return round(time.perf_counter() - start, 3)


def safe_name(value, fallback="video"):
    value = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE).strip("-._")
    return value[:80] or fallback


def parse_input_url(value):
    return douyin_resolver.extract_first_url(value) or value.strip()


def is_url(value):
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_douyin_url(value):
    host = urllib.parse.urlparse(value).netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in ("douyin.com", "iesdouyin.com"))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_identity(source, language):
    path = Path(source).expanduser()
    if not is_url(source) and path.is_file():
        identity = {"path": str(path.resolve()), "sha256": file_hash(path)}
    else:
        identity = {"url": source}
    identity["language"] = language
    identity["pipeline"] = 2
    return identity


def default_output_dir(source, metadata):
    identity = metadata["input_identity"]
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    label = safe_name(Path(urllib.parse.urlparse(source).path).stem or "video")
    return Path("outputs") / "douyin-transcriber" / f"{label}-{digest}"


def download_http(url, output_path, referer=""):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": MOBILE_USER_AGENT}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    partial = output_path.with_suffix(output_path.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
            expected = response.headers.get("Content-Length")
            if expected and out.tell() != int(expected):
                raise RuntimeError("Incomplete media download")
        if not partial.stat().st_size:
            raise RuntimeError("Empty media download")
        partial.replace(output_path)
    finally:
        partial.unlink(missing_ok=True)
    return output_path


def ffprobe_info(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return {}
    data = json.loads(result.stdout or "{}").get("format", {})
    info = {}
    if data.get("duration"):
        info["duration_seconds"] = round(float(data["duration"]), 3)
    if data.get("size"):
        info["size_bytes"] = int(data["size"])
    return info


def preview_text(path, chars=180):
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return text[:chars]


def write_summary(out_dir, metadata, timings, media_path, audio_path, result):
    raw = out_dir / "transcript_raw.txt"
    markdown = out_dir / "transcript.md"
    summary = {
        "status": "ok",
        "input_identity": metadata["input_identity"],
        "output_hashes": {name: file_hash(out_dir / name) for name in ("transcript_raw.txt", "transcript.md", "raw_result.json")},
        "title": metadata.get("title", ""),
        "author": metadata.get("author", {}),
        "video_id": metadata.get("video_id", ""),
        "source_url": metadata.get("source_url", metadata.get("input", "")),
        "media_path": str(media_path) if media_path else "",
        "audio_path": str(audio_path) if audio_path else "",
        "media_info": ffprobe_info(media_path) if media_path and Path(media_path).exists() else {},
        "audio_info": result.get("audio_info", {}),
        "utterance_count": len(result.get("result", {}).get("utterances", [])),
        "outputs": {
            "raw": str(raw),
            "markdown": str(markdown),
            "raw_result": str(out_dir / "raw_result.json"),
            "summary": str(out_dir / "summary.json"),
        },
        "timings": timings,
        "preview": preview_text(raw),
    }
    return summary


def print_summary(summary, as_json):
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print("DONE")
    if summary.get("title"):
        print(f"title={summary['title']}")
    if summary.get("video_id"):
        print(f"video_id={summary['video_id']}")
    duration = summary.get("media_info", {}).get("duration_seconds")
    if duration:
        print(f"duration={duration}s")
    print(f"transcript={summary['outputs']['raw']}")
    print(f"markdown={summary['outputs']['markdown']}")
    print(f"summary={summary['outputs']['summary']}")
    print(f"timings={json.dumps(summary['timings'], ensure_ascii=False)}")
    if summary.get("preview"):
        print(f"preview={summary['preview']}")


def maybe_print_cached(out_dir, total_start, as_json, force, identity):
    if force:
        return False
    try:
        cached = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
        if cached.get("status") != "ok" or cached.get("input_identity") != identity:
            return False
        for name in ("transcript_raw.txt", "transcript.md", "raw_result.json"):
            if file_hash(out_dir / name) != cached.get("output_hashes", {}).get(name):
                return False
    except (OSError, ValueError, TypeError, AttributeError):
        return False
    cached["status"] = "cached"
    cached.setdefault("timings", {})["total"] = elapsed_since(total_start)
    print_summary(cached, as_json)
    return True


def transcribe_audio(audio_path, audio_url, out_dir, language):
    request_id, result = doubao_flash_asr.recognize_flash(
        audio_file=audio_path,
        audio_url=audio_url,
        language=language,
    )
    write_outputs(result, out_dir)
    return request_id, result


def main():
    parser = argparse.ArgumentParser(description="One-command Douyin/local media to transcript CLI.")
    parser.add_argument("input", help="Douyin share text, Douyin URL, local video/audio file, or public audio URL.")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to outputs/douyin-transcriber/{label}-{input-hash}.")
    parser.add_argument("--work-dir", type=Path, help="Parent for isolated run directories. Defaults to {out-dir}/work.")
    parser.add_argument("--language", default="")
    parser.add_argument("--force", action="store_true", help="Re-run even if transcript_raw.txt already exists.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON only.")
    parser.add_argument("--cookies-from-browser", default="", help="Fallback yt-dlp browser cookies, for example chrome.")
    args = parser.parse_args()

    total_start = now()
    source = parse_input_url(args.input.strip())
    source_path = Path(source).expanduser()
    local = not is_url(source) and source_path.is_file()
    audio_url = source if is_url(source) and public_audio_format(source) else None
    if not local and not audio_url and not (is_url(source) and is_douyin_url(source)):
        raise RuntimeError("Input is not a Douyin URL, public audio URL, or local media file.")
    identity = input_identity(source, args.language)
    metadata = {"input": args.input, "source_url": source, "input_identity": identity}
    out_dir = (args.out_dir or default_output_dir(source, metadata)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Serialize writes to a shared output directory; never silently mix concurrent runs.
    with (out_dir / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another transcription is using this output directory.")
        if maybe_print_cached(out_dir, total_start, args.json, args.force, identity):
            return
        # An interrupted rerun must not leave an older success marker.
        (out_dir / "summary.json").unlink(missing_ok=True)
        work_parent = args.work_dir or out_dir / "work"
        work_parent.mkdir(parents=True, exist_ok=True)
        timings = {}
        with tempfile.TemporaryDirectory(prefix="run-", dir=work_parent) as temp:
            work_dir = Path(temp)
            media_path = source_path.resolve() if local else None
            audio_path = None
            if not local and not audio_url:
                start = now()
                try:
                    resolved = douyin_resolver.resolve_douyin_url(source)
                    if not resolved.get("video_url"):
                        raise RuntimeError("Resolver returned no playable video URL.")
                    media_path = download_http(resolved["video_url"], work_dir / "source.mp4",
                                               resolved.get("source_url", source))
                    metadata.update(resolved)
                except Exception as exc:
                    parsed = urllib.parse.urlparse(source)
                    if parsed.path == "/jingxuan" and "modal_id=" in parsed.query:
                        raise RuntimeError(f"Resolver/download failed: {exc}. Use the Skill's Chrome/CDP fallback.") from exc
                    try:
                        media_path = download_video(source, work_dir / "yt-dlp", args.cookies_from_browser)
                    except Exception as download_error:
                        raise RuntimeError(f"Resolver/download failed: {exc}; yt-dlp failed: {download_error}. Use the Skill's Chrome/CDP fallback.") from download_error
                timings["download"] = elapsed_since(start)
            if media_path:
                start = now()
                audio_path = media_path if media_path.suffix.lower() in AUDIO_EXTENSIONS else extract_audio(media_path, work_dir)
                timings["extract_audio"] = elapsed_since(start)
            start = now()
            request_id, result = transcribe_audio(audio_path, audio_url, out_dir, args.language)
            timings["asr"] = elapsed_since(start)
            metadata["request_id"] = request_id
            timings["total"] = elapsed_since(total_start)
            summary = write_summary(out_dir, metadata, timings, media_path, audio_path, result)
        summary["media_path"] = str(source_path.resolve()) if local else ""
        summary["audio_path"] = str(source_path.resolve()) if local and source_path.suffix.lower() in AUDIO_EXTENSIONS else ""
        pending = out_dir / "summary.json.tmp"
        pending.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        pending.replace(out_dir / "summary.json")
        print_summary(summary, args.json)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        sys.exit(1)
