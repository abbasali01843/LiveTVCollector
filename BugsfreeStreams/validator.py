"""Unified stream health validator for generated LiveTV playlists."""
from __future__ import annotations

import concurrent.futures
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

ROOT = Path("LiveTV")
OUT = Path("BugsfreeStreams/Output")
TIMEOUT = 6
WORKERS = 32
HEADERS = {"User-Agent": "LiveTVCollector-Health/1.5"}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}


def normalize_url(url: str) -> str:
    url = str(url).strip()
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, urlencode(query), ""))


def protocol(url: str, content_type: str = "") -> str:
    value = normalize_url(url).lower().split("?", 1)[0]
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
    if status == "geo_or_restricted":
        return 25
    if status == "timeout":
        return 10
    if status in {"down", "invalid"}:
        return 0
    return 15


def probe_hls(response) -> tuple[bool, str | None]:
    try:
        lines = []
        for raw in response.iter_lines():
            if raw:
                lines.append(raw)
            if len(lines) >= 40:
                break
        if b"#EXTM3U" not in b"\n".join(lines).upper():
            return False, None
        for raw in lines:
            line = raw.decode("utf-8", errors="ignore").strip()
            if line and not line.startswith("#"):
                return True, urljoin(response.url, line)
        return True, None
    except requests.RequestException:
        return False, None


def probe_segment(url: str) -> bool:
    if not url:
        return False
    try:
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            return r.status_code < 400 and bool(next(r.iter_content(chunk_size=2048), b""))
    except requests.RequestException:
        return False


def probe(channel: dict) -> dict:
    url = normalize_url(channel.get("url", ""))
    result = {
        "name": channel.get("name", "Unnamed Channel"), "url": url,
        "country": channel.get("country", ""), "group": channel.get("group", "Uncategorized"),
        "logo": channel.get("logo", ""), "source": channel.get("source", ""),
        "status": "unknown", "protocol": protocol(url), "http_status": None,
        "final_url": url, "redirected": False, "score": 0,
    }
    if not url.startswith(("http://", "https://")):
        result["status"] = "invalid"
        return result
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        result.update(
            http_status=r.status_code,
            final_url=normalize_url(r.url),
            redirected=normalize_url(r.url) != url,
            protocol=protocol(r.url, r.headers.get("content-type", "")),
        )
        if r.status_code in (401, 403, 451):
            result["status"] = "geo_or_restricted"
            result["score"] = score(result["status"], result["protocol"])
            return result
        if 200 <= r.status_code < 400 and result["protocol"] not in {"hls", "dash"}:
            result["status"] = "active"
            result["score"] = score("active", result["protocol"], result["redirected"])
            return result
    except requests.Timeout:
        result["status"] = "timeout"
        result["score"] = score("timeout", result["protocol"])
        return result
    except requests.RequestException:
        pass
    try:
        with requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result.update(
                http_status=r.status_code,
                final_url=normalize_url(r.url),
                redirected=normalize_url(r.url) != url,
                protocol=protocol(r.url, r.headers.get("content-type", "")),
            )
            if r.status_code in (401, 403, 451):
                result["status"] = "geo_or_restricted"
            elif 200 <= r.status_code < 400:
                if result["protocol"] == "hls":
                    ok, segment = probe_hls(r)
                    result.update(manifest_ok=ok, sample_segment=segment)
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
            if isinstance(grouped, dict):
                items = [x for values in grouped.values() for x in values if isinstance(x, dict)]
            elif isinstance(grouped, list):
                items = [x for x in grouped if isinstance(x, dict)]
            else:
                continue
            country = data.get("country", path.parent.name) if isinstance(data, dict) else path.parent.name
            for item in items:
                item = dict(item)
                item.setdefault("country", country)
                channels.append(item)
        except (OSError, json.JSONDecodeError):
            continue
    return channels


def compact_channel(item: dict) -> dict:
    return {
        "name": item.get("name", "Unnamed Channel"),
        "url": item.get("final_url") or item.get("url", ""),
        "logo": item.get("logo", ""),
        "group": item.get("group", "Uncategorized"),
        "country": item.get("country", ""),
        "type": item.get("protocol", "unknown"),
        "score": item.get("score", 0),
    }


def write_app_exports(results: list[dict], checked_at: str) -> None:
    active = [x for x in results if x["status"] == "active"]
    OUT.mkdir(parents=True, exist_ok=True)
    compact_active = [compact_channel(x) for x in active]
    (OUT / "active.json").write_text(
        json.dumps({"version": 1, "updated": checked_at, "count": len(compact_active), "channels": compact_active}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (OUT / "active.m3u").open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in compact_active:
            logo = ch["logo"].replace('"', "&quot;")
            group = ch["group"].replace('"', "&quot;")
            name = ch["name"].replace("\n", " ").replace("\r", " ")
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}\n{ch["url"]}\n')

    by_country = defaultdict(list)
    for item in results:
        by_country[item.get("country", "Unknown")].append(item)
    countries = {}
    country_dir = OUT / "countries"
    country_dir.mkdir(parents=True, exist_ok=True)
    for country, items in sorted(by_country.items()):
        counts = defaultdict(int)
        for item in items:
            counts[item.get("status", "unknown")] += 1
        country_active = [compact_channel(x) for x in items if x.get("status") == "active"]
        summary = {
            "total": len(items), "active": counts["active"], "geo_or_restricted": counts["geo_or_restricted"],
            "down": counts["down"], "timeout": counts["timeout"], "unknown": counts["unknown"], "invalid": counts["invalid"],
            "average_score": round(sum(x.get("score", 0) for x in items) / len(items), 2) if items else 0,
        }
        countries[country] = summary
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in country).strip("_") or "Unknown"
        (country_dir / f"{safe_name}.json").write_text(
            json.dumps({"version": 1, "updated": checked_at, "country": country, "count": len(country_active), "health": summary, "channels": country_active}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with (country_dir / f"{safe_name}.m3u").open("w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in country_active:
                logo = ch["logo"].replace('"', "&quot;")
                group = ch["group"].replace('"', "&quot;")
                name = ch["name"].replace("\n", " ").replace("\r", " ")
                f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}\n{ch["url"]}\n')
    (OUT / "countries.json").write_text(
        json.dumps({"version": 1, "updated": checked_at, "countries": countries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "manifest.json").write_text(
        json.dumps({
            "version": 1,
            "updated": checked_at,
            "endpoints": {
                "all_active_json": "active.json",
                "all_active_m3u": "active.m3u",
                "country_summary": "countries.json",
                "country_directory": "countries/",
                "full_health": "health.json",
            },
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    unique = {}
    for channel in load_channels():
        url = normalize_url(channel.get("url", ""))
        if url:
            item = dict(channel)
            item["url"] = url
            unique.setdefault(url, item)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(probe, unique.values()))
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary = defaultdict(int)
    for item in results:
        summary[item["status"]] += 1
    payload = {
        "updated": checked_at,
        "total_unique_streams": len(results),
        "summary": dict(summary),
        "active_streams": summary["active"],
        "average_score": round(sum(x["score"] for x in results) / len(results), 2) if results else 0,
        "streams": results,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "health.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_app_exports(results, checked_at)
    print(f"Validated {len(results)} unique streams: {dict(summary)}; active={summary['active']}")


if __name__ == "__main__":
    main()
