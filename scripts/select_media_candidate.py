#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


def load_urls(path, inline_urls):
    urls = list(inline_urls)
    if path:
        text = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            if isinstance(data, list):
                urls.extend(item["url"] if isinstance(item, dict) else item for item in data)
            elif isinstance(data, dict):
                for value in data.values():
                    if isinstance(value, str) and value.startswith("http"):
                        urls.append(value)
                    elif isinstance(value, list):
                        urls.extend(item for item in value if isinstance(item, str) and item.startswith("http"))
        except json.JSONDecodeError:
            urls.extend(line.strip() for line in text.splitlines() if line.strip().startswith("http"))
    return list(dict.fromkeys(urls))


def ffprobe_duration(url, referer):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-user_agent",
        USER_AGENT,
    ]
    if referer:
        command.extend(["-headers", f"Referer: {referer}\r\n"])
    command.extend(["-show_entries", "format=duration", "-of", "json", url])
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
    if result.returncode != 0:
        return None, result.stderr.strip()
    data = json.loads(result.stdout or "{}")
    duration = data.get("format", {}).get("duration")
    return float(duration) if duration else None, ""


def main():
    parser = argparse.ArgumentParser(description="Rank Douyin media URLs by ffprobe duration.")
    parser.add_argument("urls", nargs="*", help="Candidate media URLs.")
    parser.add_argument("--from-file", help="Text or JSON file containing candidate URLs.")
    parser.add_argument("--expected-duration", type=float, help="Expected duration in seconds.")
    parser.add_argument("--referer", default="", help="Referer header, usually the Douyin page URL.")
    parser.add_argument("--out-json", help="Write ranked candidates to this JSON file.")
    args = parser.parse_args()

    ranked = []
    for url in load_urls(args.from_file, args.urls):
        duration, error = ffprobe_duration(url, args.referer)
        score = None
        if duration is not None and args.expected_duration is not None:
            score = abs(duration - args.expected_duration)
        ranked.append({"url": url, "duration": duration, "score": score, "error": error})

    ranked.sort(key=lambda item: (item["score"] is None, item["score"] if item["score"] is not None else 10**9))
    payload = {"best": ranked[0] if ranked else None, "candidates": ranked}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out_json:
        Path(args.out_json).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        sys.exit(1)
