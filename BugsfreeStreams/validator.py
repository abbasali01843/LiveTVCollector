"""Unified stream health validator for generated LiveTV playlists."""
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path("LiveTV")
OUT = Path("BugsfreeStreams/Output")
TIMEOUT = 6
WORKERS = 32
HEADERS = {"User-Agent": "LiveTVCollector-Health/1.1"}


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


def score(status: str, proto: str, redirected: bool = False) -> int:
    if status == "active":
        value = 100 if proto in {"hls", "dash", "media"} else 80
        return max(0, value - (5 if redirected else 0))
    if status == "geo_or_restricted": return 25
    if status == "timeout": return 10
    if status == "down": return 0
    return 15


def probe_hls(url: str, response) -> tuple[bool, str | None]:
    try:
        sample = b"\n".join(list(response.iter_lines())[:40])
        if b"#EXTM3U" not in sample.upper():
            return False, None
        for raw in sample.splitlines():
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line or line.startswith("#"): continue
            return True, urljoin(response.url, line)
        return True, None
    except requests.RequestException:
        return False, None


def probe(channel: dict) -> dict:
    url = str(channel.get("url", "")).strip()
    result = {
        "name": channel.get("name", "Unnamed Channel"), "url": url,
        "country": channel.get("country", ""), "group": channel.get("group", "Uncategorized"),
        "source": channel.get("source", ""), "status": "unknown", "protocol": protocol(url),
        "http_status": None, "final_url": url, "redirected": False, "score": 0,
    }
    if not url.startswith(("http://", "https://")):
        result["status"] = "invalid"; result["score"] = 0; return result
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result["http_status"] = r.status_code; result["final_url"] = r.url
        result["redirected"] = r.url != url
        result["protocol"] = protocol(r.url, r.headers.get("content-type", ""))
        if 200 <= r.status_code < 400 and result["protocol"] != "hls":
            result["status"] = "active"; result["score"] = score(result["status"], result["protocol"], result["redirected"]); return result
    except requests.RequestException:
        pass
    try:
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code; result["final_url"] = r.url
            result["redirected"] = r.url != url
            result["protocol"] = protocol(r.url, r.headers.get("content-type", ""))
            if 200 <= r.status_code < 400:
                if result["protocol"] == "hls":
                    ok, segment = probe_hls(r.url, r)
                    result["manifest_ok"] = ok
                    result["sample_segment"] = segment
                    result["status"] = "active" if ok else "unknown"
                else:
                    result["status"] = "active"
            elif r.status_code in (401, 403, 451):
                result["status"] = "geo_or_restricted"
            else:
                result["status"] = "down"
    except requests.Timeout:
        result["status"] = "timeout"
    except requests.RequestException:
        result["status"] = "down"
    result["score"] = score(result["status"], result["protocol"], result["redirected"])
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
        url = str(channel.get("url", "")).strip()
        if url: unique.setdefault(url, channel)
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
