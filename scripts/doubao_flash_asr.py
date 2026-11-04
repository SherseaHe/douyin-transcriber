#!/usr/bin/env python3
import argparse
import base64
import json
import sys
import uuid
from pathlib import Path

from asr_common import OK_CODE, get_api_key, post_json, write_transcript_outputs


FLASH_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
FLASH_RESOURCE_ID = "volc.bigasr.auc_turbo"


def file_to_base64(audio_path):
    return base64.b64encode(audio_path.read_bytes()).decode("utf-8")


def recognize_flash(audio_file, audio_url, language):
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("Missing VOLC_ASR_API_KEY. Set it before running this script.")

    request_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Api-Resource-Id": FLASH_RESOURCE_ID,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }

    if audio_file:
        audio = {"data": file_to_base64(audio_file)}
    elif audio_url:
        audio = {"url": audio_url}
    else:
        raise ValueError("Provide --audio-file or --audio-url.")

    if language:
        audio["language"] = language

    body = {
        "user": {"uid": "codex-douyin-transcript"},
        "audio": audio,
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "show_utterances": True,
        },
    }

    headers, response_body = post_json(FLASH_URL, headers, body)
    status = headers.get("X-Api-Status-Code")
    if status != OK_CODE:
        message = headers.get("X-Api-Message", "")
        logid = headers.get("X-Tt-Logid", "")
        raise RuntimeError(f"Flash recognize failed: {status} {message} logid={logid} body={response_body}")

    return request_id, json.loads(response_body)


def write_outputs(result, out_dir):
    return write_transcript_outputs(result, out_dir)


def main():
    parser = argparse.ArgumentParser(description="Transcribe a local audio file with Doubao ASR flash mode.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--audio-file", type=Path, help="Local mp3/wav/ogg file to send as base64.")
    source.add_argument("--audio-url", help="Publicly reachable mp3/wav/ogg audio URL.")
    parser.add_argument("--language", default="", help="Optional language code, for example zh-CN or en-US.")
    parser.add_argument("--out-dir", default="outputs/douyin-transcriber/flash-result")
    args = parser.parse_args()

    if args.audio_file and not args.audio_file.exists():
        raise FileNotFoundError(args.audio_file)

    request_id, result = recognize_flash(args.audio_file, args.audio_url, args.language)
    out_dir = Path(args.out_dir)
    write_outputs(result, out_dir)

    print(f"request_id={request_id}")
    print(f"raw_result={out_dir / 'raw_result.json'}")
    print(f"transcript={out_dir / 'transcript_raw.txt'}")
    print(f"markdown={out_dir / 'transcript.md'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        sys.exit(1)
