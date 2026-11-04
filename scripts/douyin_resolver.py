#!/usr/bin/env python3
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request


USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1"
)


def extract_first_url(value):
    match = re.search(r"https?://[^\s]+", value)
    if not match:
        return ""
    return match.group(0).rstrip("，。,.!！?？;；)")


def parse_video_id(url):
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if query.get("modal_id"):
        return query["modal_id"][0]
    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        return parts[-1]
    return ""


def request_text(url, allow_redirects=True):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = urllib.request.build_opener()
    if not allow_redirects:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace"), response.geturl(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            return "", exc.headers.get("Location", ""), dict(exc.headers)
        raise


def maybe_json_loads(raw):
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def convert_video_data(data):
    video = data.get("video", {})
    play_addr = video.get("play_addr") or video.get("playAddr") or {}
    cover = video.get("cover") or {}
    urls = play_addr.get("url_list") or []
    cover_urls = cover.get("url_list") or []
    video_url = urls[0].replace("playwm", "play") if urls else ""
    return {
        "title": data.get("desc", ""),
        "video_url": video_url,
        "cover_url": cover_urls[0] if cover_urls else "",
        "author": {
            "name": data.get("author", {}).get("nickname", ""),
            "uid": data.get("author", {}).get("sec_uid", ""),
        },
    }


def extract_video_data(html_text, video_id):
    patterns = [
        r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
        r"<script[^>]*id=[\"']RENDER_DATA[\"'][^>]*>(.+?)</script>",
        r"window\._SSR_HYDRATED_DATA\s*=\s*({.+?});",
        r"window\.RENDER_DATA\s*=\s*({.+?});",
    ]

    for pattern in patterns:
        match = re.search(pattern, html_text, re.DOTALL)
        if not match:
            continue
        raw = html.unescape(match.group(1).strip())
        if "%" in raw:
            raw = urllib.parse.unquote(raw)
        data = maybe_json_loads(raw)
        if not data:
            continue

        loader = data.get("loaderData", {})
        for key in (f"video_{video_id}/page", "video_(id)/page"):
            items = loader.get(key, {}).get("videoInfoRes", {}).get("item_list", [])
            if items:
                return items[0]

        scope = data.get("defaultScope", {})
        for key in ("videoData", "aweme"):
            if isinstance(scope.get(key), dict):
                return scope[key]

    return None


def resolve_douyin_url(input_text):
    url = extract_first_url(input_text) or input_text
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "v.douyin.com":
        _, redirected, _ = request_text(url, allow_redirects=False)
        if redirected:
            url = redirected
            parsed = urllib.parse.urlparse(url)

    video_id = parse_video_id(url)
    if not video_id:
        raise RuntimeError("Could not extract a Douyin video id.")

    share_url = f"https://www.iesdouyin.com/share/video/{video_id}"
    page, _, _ = request_text(share_url)
    data = extract_video_data(page, video_id)
    if not data:
        raise RuntimeError("Could not extract SSR video data. Use Chrome/CDP fallback for this URL.")

    result = convert_video_data(data)
    result["video_id"] = video_id
    result["source_url"] = url
    result["share_url"] = share_url
    return result


def main():
    parser = argparse.ArgumentParser(description="Fast HTTP resolver for simple Douyin video URLs.")
    parser.add_argument("input", help="Douyin URL or pasted share text.")
    args = parser.parse_args()
    print(json.dumps(resolve_douyin_url(args.input), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        sys.exit(1)
