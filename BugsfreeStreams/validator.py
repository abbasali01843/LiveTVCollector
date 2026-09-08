"""Unified stream health validator for generated LiveTV playlists."""
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

ROOT = Path("LiveTV")
OUT = Path("BugsfreeStreams/Output")
TIMEOUT = 6
WORKERS = 32
HEADERS = {"User-Agent": "LiveTVCollector-Health/1.3"}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}


def normalize_url(url: str) -> str:
    url = url.strip()
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, urlencode(query), ""))


def protocol(url: str, content_type: str = "") -> str:
    value = url.lower().split("?", 1)[0]
    ct = content_type.lower()
    if value.endswith(".m3u8") or "mpegurl" in ct or "vnd.apple.mpegurl" in ct:
        return "hls"
    if value.endswith(".mpd") or "dash+xml" in ct:
        return "dash"
    if value.endswith((".mp4", ".ts", ".mkv", ".webm", ".avi", ".flv")):
        return "media"
    return "unknown"


def score(status: str, proto: str, redirected: bool = False, segment_ok: bool | None = None) -> int:
    if status == "active":
        value = 100 if proto in {"hls", "dash", "media"} else 80
        if segment_ok is False:
            value -= 35
        return max(0, value - (5 if redirected else 0))
    if status == "geo_or_restricted": return 25
    if status == "timeout": return 10
    if status == "down": return 0
    return 15


def probe_hls(response) -> tuple[bool, str | None]:
    try:
        lines = []
        for raw in response.iter_lines():
            if raw:
                lines.append(raw)
            if len(lines) >= 40:
                break
        sample = b"\n".join(lines)
        if b"#EXTM3U" not in sample.upper():
            return False, None
        for raw in lines:
            line = raw.decode("utf-8", errors="ignore").strip()
            if line and not line.startswith("#"):
                return True, urljoin(response.url, line)
        return True, None
    except requests.RequestException:
        return False, None


def probe_segment(url: str) -> bool:
    try:
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            if r.status_code >= 400:
                return False
            return bool(next(r.iter_content(chunk_size=2048), b""))
    except requests.RequestException:
        return False


def probe(channel: dict) -> dict:
    url = normalize_url(str(channel.get("url", "")))
    result = {
        "name": channel.get("name", "Unnamed Channel"), "url": url,
        "country": channel.get("country", ""), "group": channel.get("group", "Uncategorized"),
        "source": channel.get("source", ""), "status": "unknown", "protocol": protocol(url),
        "http_status": None, "final_url": url, "redirected": False, "score": 0,
    }
    if not url.startswith(("http://", "https://")):
        result["status"] = "invalid"; return result

    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result["http_status"] = r.status_code; result["final_url"] = normalize_url(r.url)
        result["redirected"] = result["final_url"] != url
        result["protocol"] = protocol(r.url, r.headers.get("content-type", ""))
        if r.status_code in (401, 403, 451):
            result["status"] = "geo_or_restricted"
            result["score"] = score(result["status"], result["protocol"])
            return result
        if 200 <= r.status_code < 400 and result["protocol"] not in {"hls", "dash"}:
            result["status"] = "active"
            result["score"] = score(result["status"], result["protocol"], result["redirected"])
            return result
    except requests.Timeout:
        result["status"] = "timeout"
        result["score"] = score(result["status"], result["protocol"])
        return result
    except requests.RequestException:
        pass

    try:
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code; result["final_url"] = normalize_url(r.url)
            result["redirected"] = result["final_url"] != url
            result["protocol"] = protocol(r.url, r.headers.get("content-type", ""))
            if r.status_code in (401, 403, 451):
                result["status"] = "geo_or_restricted"
            elif 200 <= r.status_code < 400:
                if result["protocol"] == "hls":
                    ok, segment = probe_hls(r)
                    result["manifest_ok"] = ok
                    result["sample_segment"] = segment
                    result["segment_ok"] = probe_segment(segment) if ok and segment else None
                    result["status"] = "active" if ok and result["segment_ok"] is not False else "unknown"
                elif result["protocol"] == "dash":
                    chunk = next(r.iter_content(chunk_size=16384), b"")
                    result["manifest_ok"] = b"<MPD" in chunk or b":MPD" in chunk
                    result["status"] = "active" if result["manifest_ok"] else "unknown"
                else:
                    result["status"] = "active"
            else:
                result["status"] = "down"
    except requests.Timeout:
        result["status"] = "timeout"
    except requests.RequestException:
        result["status"] = "down"
    result["score"] = score(result["status"], result["protocol"], result["redirected"], result.get("segment_ok"))
    return result


def load_channels() -> list[dict]:
    channels = []
    for path in ROOT.glob("*/LiveTV.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            grouped = data.get("channels", []) if isinstance(data, dict) else data
            if isinstance(grouped, dict): items = [x for values in grouped.values() for x in values if isinstance(x, dict)]
            elif isinstance(grouped, list): items = [x for x in grouped if isinstance(x, dict)]
            else: continue
            country = data.get("country", path.parent.name) if isinstance(data, dict) else path.parent.name
            for item in items:
                item = dict(item); item.setdefault("country", country); channels.append(item)
        except (OSError, json.JSONDecodeError):
            continue
    return channels


def main() -> None:
    channels = load_channels(); unique = {}
    for channel in channels:
        url = normalize_url(str(channel.get("url", "")))
        if url:
            channel = dict(channel); channel["url"] = url
            unique.setdefault(url, channel)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe, unique.values()))
    summary = {}
    for item in results: summary[item["status"]] = summary.get(item["status"], 0) + 1
    payload = {
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "total_unique_streams": len(results), "summary": summary,
        "active_streams": sum(x["status"] == "active" for x in results),
        "average_score": round(sum(x["score"] for x in results) / len(results), 2) if results else 0,
        "streams": results,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "health.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {len(results)} unique streams: {summary}")


if __name__ == "__main__": main()
