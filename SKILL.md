---
name: douyin-transcriber
description: "提取抖音分享链接或本地音视频的口播文字，输出 TXT、Markdown 和识别结果 JSON。用于转写、提取文案或基于口播总结；不负责画面理解或字幕 OCR。"
---

# Douyin Transcriber

Use FFmpeg and Doubao flash ASR to transcribe speech. Resolve script paths relative to this file. For installation and credentials, read [docs/configuration.md](docs/configuration.md). Supported runtime: Python 3.10+ on macOS/Linux; Windows users need WSL.

## Workflow

1. Run the main CLI once; do not separately repeat its resolver first:

   ```bash
   python3 "<skill-dir>/scripts/douyin_transcribe.py" "INPUT" --json
   ```

   `INPUT` can be a Douyin share text/URL, a local media file, or a public MP3/WAV/OGG URL. Other local formats such as M4A are converted through FFmpeg. Local files are preserved. Audio is sent to Doubao ASR; this may incur provider charges.
2. Read `summary.json` and `transcript_raw.txt`. Return links to the transcript and a short preview. Summaries must be grounded in the transcript. Do not claim to have inspected the pictures or translate the transcript without distinguishing the translation.
3. On HTTP/yt-dlp access failures, use the browser fallback below if available. Do not keep retrying legacy Douyin APIs. For `jingxuan?modal_id=...`, the CLI intentionally stops after resolver/download failure instead of trying yt-dlp.
4. On ASR failure, report the failing stage. Do not fabricate text or automatically retry paid requests. Check credentials and service permissions first.

## Cache and output

Results: `transcript_raw.txt`, `transcript.md`, `raw_result.json`, `summary.json` under `outputs/douyin-transcriber/{label}-{input-hash}` or `--out-dir`.

Cache requires matching input identity, language and result checksums. Local identity includes absolute path and content hash. URL identity uses the exact input URL: `--force` refreshes content at an unchanged URL. Different short/long links may produce separate caches. Failed runs do not leave a success marker. Each run has an isolated temporary directory, cleaned on success or failure; `--work-dir` sets its parent. Concurrent writes to one output directory are rejected. SRT export is not implemented.

## Browser fallback

This is an Agent-assisted step, not automatic browser control in the CLI. Use the available browser tool and its instructions; no specific browser plugin is required.

- Confirm the target title, video ID and displayed duration. A recommendation/preloaded video is not the target.
- Check whether the current user has explicitly authorized extracting and temporarily saving this video's media URLs, including short-lived signed URLs. Ask only if that authorization is missing. This public Skill does not carry authorization from its author to other users.
- Read the target video's `currentSrc`/source. A `blob:` URL cannot be downloaded outside the browser. In that case inspect the page's loaded media resource entries for candidate URLs.
- Match candidate duration to the player, and inspect stream types: Douyin may load separate video-only and audio-only resources. Prefer the matching audio stream for transcription. The helper `scripts/select_media_candidate.py --from-file PATH --expected-duration SECONDS --referer PAGE_URL` ranks by duration only; its output contains URLs, so keep it in temporary storage and do not echo it into chat or logs.
- Download the authorized media to a temporary file, then run the main CLI on that file with a stable `--out-dir`. Use the required Referer/User-Agent when the CDN needs them.
- Delete temporary URL files on success or failure. Delete downloaded temporary media when finished; preserve user-supplied original files. Do not retain signed URLs in summaries, transcripts or permanent artifacts. Note that a CLI run on a temporary local file uses that file's identity, not the original Douyin link.
- Do not read/export browser cookies or other credentials without separate explicit authorization. Do not bypass tool approvals. The CLI option `--cookies-from-browser` reads browser cookies through yt-dlp and must not be enabled implicitly.

## Verification

```bash
python3 -B "<skill-dir>/scripts/test_transcribe.py"
```

Offline regression tests mock ASR/network and include actual FFmpeg extraction. They do not require a key or call a paid API.
