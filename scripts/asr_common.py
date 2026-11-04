import json
import os
import urllib.error
import urllib.request

OK_CODE = "20000000"

def post_json(url, headers, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            return response.headers, response_body
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {response_body}") from exc


def get_api_key():
    return os.environ.get("VOLC_ASR_API_KEY", "").strip()


def write_markdown(transcript, path, title="Transcript"):
    body = transcript.strip()
    if body:
        path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    else:
        path.write_text(f"# {title}\n", encoding="utf-8")


def write_transcript_outputs(result, out_dir, title="Transcript"):
    out_dir.mkdir(parents=True, exist_ok=True)

    result_path = out_dir / "raw_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    asr_result = result.get("result", {})
    transcript = asr_result.get("text", "")
    transcript_path = out_dir / "transcript_raw.txt"
    markdown_path = out_dir / "transcript.md"

    transcript_path.write_text(transcript, encoding="utf-8")
    write_markdown(transcript, markdown_path, title=title)

    return {
        "raw_result": str(result_path),
        "transcript": str(transcript_path),
        "markdown": str(markdown_path),
    }
