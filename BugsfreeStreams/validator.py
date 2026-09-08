"""Unified stream health validator for generated LiveTV playlists."""
from __future__ import annotations

import concurrent.futures
import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests

ROOT = Path("LiveTV")
OUT = Path("BugsfreeStreams/Output")
TIMEOUT = 6
HEAD_TIMEOUT = 4
WORKERS = 32
HEADERS = {"User-Agent": "LiveTVCollector-Health/1.6", "Accept": "*/*"}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}
TRANSIENT_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_thread_local = threading.local()


def session() -> requests.Session:
    """Reuse HTTP connections independently in each worker thread."""
    value = getattr(_thread_local, "session", None)
    if value is None:
        value = requests.Session()
        value.headers.update(HEADERS)
        _thread_local.session = value
    return value


def normalize_url(url: str) -> str:
    url = str(url).strip()
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    return urlunparse(
        (p.scheme.lower(), p.netloc.lower(), p.path, p.params, urlencode(query), "")
    )


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


def score(
    status: str,
    proto: str,
    redirected: bool = False,
    segment_ok: bool | None = None,
) -> int:
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
    """Validate the playlist header and return a sample child/segment URI."""
    try:
        lines = []
        for raw in response.iter_lines():
            if raw:
                lines.append(raw)
            if len(lines) >= 64:
                break
        blob = b"\n".join(lines).upper()
        if b"#EXTM3U" not in blob:
            return False, None
        for raw in lines:
            line = raw.decode("utf-8", errors="ignore").strip()
            if line and not line.startswith("#"):
                return True, urljoin(response.url, line)
        return True, None
    except requests.RequestException:
        return False, None


def probe_segment(url: str) -> bool:
    """Read a small amount of the sample URI so reachability means data, not only 200."""
    if not url:
        return False
    try:
        with session().get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            if r.status_code >= 400:
                return False
            chunk = next(r.iter_content(chunk_size=2048), b"")
            return bool(chunk)
    except requests.RequestException:
        return False


def probe_hls_sample(url: str, depth: int = 0) -> bool:
    """Validate either a media segment or one nested HLS playlist."""
    if not url:
        return False
    if depth > 1:
        return probe_segment(url)
    try:
        with session().get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            if r.status_code >= 400:
                return False
            proto = protocol(r.url, r.headers.get("content-type", ""))
            if proto != "hls":
                return bool(next(r.iter_content(chunk_size=2048), b""))
            ok, child = probe_hls(r)
            if not ok:
                return False
            if child:
                return probe_hls_sample(child, depth + 1)
            return True
    except requests.RequestException:
        return False


def _apply_response(result: dict, response) -> None:
    result.update(
        http_status=response.status_code,
        final_url=normalize_url(response.url),
        redirected=normalize_url(response.url) != result["url"],
        protocol=protocol(response.url, response.headers.get("content-type", "")),
    )


def _get_once(url: str):
    return session().get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)


def probe(channel: dict) -> dict:
    url = normalize_url(channel.get("url", ""))
    result = {
        "name": channel.get("name", "Unnamed Channel"),
        "url": url,
        "country": channel.get("country", ""),
        "group": channel.get("group", "Uncategorized"),
        "logo": channel.get("logo", ""),
        "source": channel.get("source", ""),
        "status": "unknown",
        "protocol": protocol(url),
        "http_status": None,
        "final_url": url,
        "redirected": False,
        "score": 0,
    }
    if not url.startswith(("http://", "https://")):
        result["status"] = "invalid"
        return result

    # HEAD is cheap, but many streaming hosts reject it. A timeout must also fall
    # through to GET rather than immediately classifying a reachable stream as dead.
    try:
        r = session().head(url, timeout=HEAD_TIMEOUT, allow_redirects=True)
        _apply_response(result, r)
        if r.status_code in (401, 403, 451):
            result["status"] = "geo_or_restricted"
            result["score"] = score(result["status"], result["protocol"])
            return result
        if 200 <= r.status_code < 400 and result["protocol"] not in {"hls", "dash", "media"}:
            result["status"] = "active"
            result["score"] = score("active", result["protocol"], result["redirected"])
            return result
    except requests.RequestException:
        pass

    # GET is authoritative for HLS/DASH and is the fallback for HEAD failures.
    for attempt in range(2):
        try:
            with _get_once(url) as r:
                _apply_response(result, r)
                if r.status_code in (401, 403, 451):
                    result["status"] = "geo_or_restricted"
                elif r.status_code in TRANSIENT_STATUSES and attempt == 0:
                    continue
                elif 200 <= r.status_code < 400:
                    if result["protocol"] == "hls":
                        ok, sample = probe_hls(r)
                        result.update(manifest_ok=ok, sample_segment=sample)
                        result["segment_ok"] = probe_hls_sample(sample) if ok and sample else None
                        if not ok:
                            result["status"] = "unknown"
                        elif sample:
                            result["status"] = "active" if result["segment_ok"] else "unknown"
                        else:
                            # A valid master/media playlist without a sample URI is
                            # useful but cannot be fully stream-probed.
                            result["status"] = "active"
                    elif result["protocol"] == "dash":
                        chunk = next(r.iter_content(chunk_size=65536), b"")
                        text = chunk.decode("utf-8", errors="ignore").lstrip("\ufeff \t\r\n")
                        result["manifest_ok"] = "<MPD" in text.upper()
                        result["status"] = "active" if result["manifest_ok"] else "unknown"
                    else:
                        content_type = r.headers.get("content-type", "").lower()
                        chunk = next(r.iter_content(chunk_size=2048), b"")
                        looks_html = "text/html" in content_type or chunk.lstrip().lower().startswith((b"<!doctype html", b"<html"))
                        result["status"] = "unknown" if looks_html or not chunk else "active"
                else:
                    result["status"] = "down"
                break
        except requests.Timeout:
            if attempt == 0:
                continue
            result["status"] = "timeout"
        except requests.RequestException:
            result["status"] = "down"

    result["score"] = score(
        result["status"], result["protocol"], result["redirected"], result.get("segment_ok")
    )
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


def _safe_country_name(country: str, used: set[str]) -> str:
    base = "".join(c if c.isalnum() or c in "-_" else "_" for c in country).strip("_") or "Unknown"
    name = base
    index = 2
    while name in used:
        name = f"{base}_{index}"
        index += 1
    used.add(name)
    return name


def _write_m3u(path: Path, channels: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            logo = ch["logo"].replace("\\", "\\\\").replace('"', "&quot;")
            group = ch["group"].replace("\\", "\\\\").replace('"', "&quot;")
            name = ch["name"].replace("\n", " ").replace("\r", " ")
            f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}\n{ch["url"]}\n')


def write_app_exports(results: list[dict], checked_at: str) -> None:
    active = [x for x in results if x["status"] == "active"]
    OUT.mkdir(parents=True, exist_ok=True)
    compact_active = [compact_channel(x) for x in active]
    (OUT / "active.json").write_text(
        json.dumps({"version": 1, "updated": checked_at, "count": len(compact_active), "channels": compact_active}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_m3u(OUT / "active.m3u", compact_active)

    by_country = defaultdict(list)
    for item in results:
        by_country[item.get("country", "Unknown")].append(item)
    countries = {}
    country_dir = OUT / "countries"
    country_dir.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    for country, items in sorted(by_country.items()):
        counts = defaultdict(int)
        for item in items:
            counts[item.get("status", "unknown")] += 1
        country_active = [compact_channel(x) for x in items if x.get("status") == "active"]
        summary = {
            "total": len(items),
            "active": counts["active"],
            "geo_or_restricted": counts["geo_or_restricted"],
            "down": counts["down"],
            "timeout": counts["timeout"],
            "unknown": counts["unknown"],
            "invalid": counts["invalid"],
            "average_score": round(sum(x.get("score", 0) for x in items) / len(items), 2) if items else 0,
        }
        countries[country] = summary
        safe_name = _safe_country_name(country, used_names)
        (country_dir / f"{safe_name}.json").write_text(
            json.dumps({"version": 1, "updated": checked_at, "country": country, "count": len(country_active), "health": summary, "channels": country_active}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _write_m3u(country_dir / f"{safe_name}.m3u", country_active)
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
