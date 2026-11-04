# Douyin Transcriber — Video-to-Text Agent Skill & Python CLI

[中文](README.md) | English · [Configuration reference (Chinese)](docs/configuration.md) · [Agent workflow](SKILL.md) · [Issues](https://github.com/SherseaHe/douyin-transcriber/issues)

**Douyin Transcriber is an MIT-licensed speech transcription tool for Douyin links and local audio/video files.** It uses FFmpeg and Doubao ASR to extract spoken content into TXT, Markdown and JSON. Use it as an Agent Skill or a standalone Python CLI to prepare transcripts for notes, content analysis or subsequent AI summarization.

Douyin is the Chinese video platform. This project does not support international TikTok URLs.

## At a glance

| Item | Details |
| --- | --- |
| Inputs | Douyin share text, short/full links, local media, public MP3/WAV/OGG URLs |
| Outputs | Plain-text transcript, Markdown transcript, raw ASR JSON, run-summary JSON |
| ASR provider | Volcengine Doubao flash recording recognition, `volc.bigasr.auc_turbo` |
| Runtime | Python 3.10+, FFmpeg/ffprobe; yt-dlp for direct Douyin downloading |
| Platforms | macOS and Linux; Windows requires WSL because the CLI uses POSIX file locking |
| Agent integration | SKILL.md workflow, tested in a Codex context; browser assistance requires an available browser tool |
| License and cost | MIT source code; cloud ASR usage may be billed by the provider |
| Not included | Visual understanding, OCR, automatic translation, SRT export or a local ASR backend |

## Install and configure

On macOS:

```bash
brew install python ffmpeg yt-dlp
mkdir -p ~/.agents/skills
git clone https://github.com/SherseaHe/douyin-transcriber.git ~/.agents/skills/douyin-transcriber
cd ~/.agents/skills/douyin-transcriber
```

The destination must not already exist. Back up or compare any existing installation before replacing it. Other Agent clients may use different Skill directories. You can also clone to a regular directory and use the CLI without an Agent.

On Ubuntu/Debian, install Python 3.10+, FFmpeg and pipx, then install yt-dlp with pipx:

```bash
sudo apt update
sudo apt install python3 ffmpeg pipx
pipx install yt-dlp
pipx ensurepath
```

Enable **Doubao flash recording recognition** in the Volcengine speech console and obtain an API Key with access to `volc.bigasr.auc_turbo`. See the provider's [API documentation](https://docs.volcengine.com/docs/doubao-voice/recording-file-recognition-lite-http?lang=zh).

Set the key in the environment of the process running the CLI:

```bash
export VOLC_ASR_API_KEY='replace-with-your-api-key'
```

This is a placeholder, not a working credential. Use your runner's secret settings or interactive shell input to avoid saving real keys in shell history. The [configuration reference](docs/configuration.md#4-设置密钥) includes interactive examples.

The public CLI reads only environment variables. It does not load `.env` or read `~/.zshrc`. Desktop Agent apps may not inherit variables from your terminal; configure their execution environment separately. Python application scripts use the standard library only.

## Usage

Run from the repository directory:

```bash
# Douyin share link or an entire share message, as one quoted argument
python3 scripts/douyin_transcribe.py 'https://v.douyin.com/SHARE_CODE/' --json

# Local video or audio; M4A is converted through FFmpeg
python3 scripts/douyin_transcribe.py '/path/to/video.mp4' --out-dir outputs/example

# Force a refresh or request a language
python3 scripts/douyin_transcribe.py '/path/to/audio.m4a' --force --language en-US
```

In an Agent that has loaded the Skill:

```text
Use $douyin-transcriber to transcribe the spoken content of this video: <Douyin URL>
```

## Outputs and reliability

- `transcript_raw.txt`: recognized speech.
- `transcript.md`: the same transcript in Markdown.
- `raw_result.json`: provider response, including utterances when returned.
- `summary.json`: input identity, output checksums, timing, paths and a preview.

The default output directory is `outputs/douyin-transcriber/{label}-{input-hash}` under the current working directory. Cache reuse checks input identity, language and output checksums. Local identity includes the absolute path and file content. URL identity uses the supplied URL; use `--force` if content at that URL has changed. Short and full URLs may have separate caches.

Downloads use isolated temporary directories. Partial downloads are not reused, failed reruns invalidate the success marker, and concurrent writes to the same output directory are rejected. Original local input files are preserved. Results can include local paths and input URLs: review them before sharing.

## Frequently asked questions

### Can this extract the text from a Douyin video?

It extracts **spoken audio**. It does not read text visible in frames or image posts. Use a separate OCR workflow for on-screen text.

### Is it free and offline?

The code is MIT-licensed. Audio extraction runs locally, but recognition sends audio to Volcengine Doubao ASR and may incur charges. There is no local Whisper backend. The regression tests mock ASR and run offline.

### Does it automatically summarize or translate videos?

No. The CLI produces transcripts in the recognized language. An Agent can subsequently summarize or translate `transcript.md`; those are separate steps. A transcript-based summary is not visual analysis.

### What if Douyin returns 403 or asks for fresh cookies?

The CLI tries page resolution and yt-dlp; direct download is not guaranteed. An Agent can use the [browser fallback workflow](SKILL.md#browser-fallback) after the user authorizes temporary media URL extraction. Browser playback may use separate audio/video streams, so verify title, duration and stream type. Signed media URLs must remain temporary and be deleted after processing. Cookie access requires separate authorization.

### Does it support TikTok, Bilibili or Xiaohongshu links?

No. URL handling targets Douyin. Lawfully obtained local audio/video files can still be transcribed regardless of their original platform.

## Validation

```bash
python3 -B scripts/test_transcribe.py
```

Eight regression tests cover cache isolation, changed inputs, damaged output, failed reruns, temporary downloads, partial-file cleanup, concurrent writes and real FFmpeg extraction. Tests need FFmpeg/ffprobe but no API Key or paid API calls. macOS has been tested; native Windows is not supported.

One manual test on 2026-11-04 transcribed approximately 16 minutes 30 seconds of English audio using browser-assisted acquisition. ASR returned 179 utterances in about 10.7 seconds, and a second run used the cache. This is a single observation, not a performance benchmark; ASR timing excludes browsing and downloading. Word error rate was not measured. Third-party media and transcripts are not included in the repository.

## License

[MIT](LICENSE). The license covers this repository's code and documentation, not third-party media. Use content you are authorized to process.
