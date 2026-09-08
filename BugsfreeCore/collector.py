"""Shared collector core for LiveTVCollector.

Parses M3U/JSON/HTML sources, normalizes channels, deduplicates URLs and
optionally performs lightweight protocol-aware health checks.
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests

LOG = logging.getLogger(__name__)
DEFAULT_LOGO = "https://abbasali01843.github.io/LiveTVCollector/BugsfreeLogo/default-logo.png"
HEADERS = {"User-Agent": "LiveTVCollector/2.3 (+https://github.com/abbasali01843/LiveTVCollector)"}


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.links.extend(v for k, v in attrs if k.lower() == "href" and v)


def normalize_url(url: str) -> str:
    url = url.strip()
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        return url
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, urlencode(query), ""))


class Collector:
    def __init__(self, country: str, base_dir: str = "LiveTV", check_links: bool = False,
                 max_workers: int = 20, timeout: float = 8, file_prefix: str = "LiveTV"):
        self.country = country
        self.output_dir = os.path.join(base_dir, country)
        self.file_prefix = file_prefix or "LiveTV"
        self.check_links = check_links
        self.max_workers = max_workers
        self.timeout = timeout
        self.channels: list[dict] = []
        self._seen: set[str] = set()
        self._lock = threading.Lock()
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch(self, url: str) -> tuple[str, str]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=self.timeout, allow_redirects=True)
            r.raise_for_status()
            return r.text, r.url
        except requests.RequestException as exc:
            LOG.warning("Fetch failed: %s (%s)", url, exc)
            return "", url

    @staticmethod
    def _attrs(extinf: str) -> dict:
        return {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', extinf)}

    def add(self, name: str, url: str, group: str = "Uncategorized", logo: str = DEFAULT_LOGO,
            source: str = "", extra: dict | None = None):
        url = normalize_url(url)
        if not re.match(r"^https?://", url, re.I):
            return
        with self._lock:
            if url in self._seen:
                return
            self._seen.add(url)
            item = {"name": name.strip() or "Unnamed Channel", "url": url,
                    "group": group.strip() or "Uncategorized", "logo": logo or DEFAULT_LOGO,
                    "country": self.country, "source": source}
            if extra:
                item.update(extra)
            self.channels.append(item)

    def parse_m3u(self, text: str, source: str):
        pending = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#EXTINF:"):
                attrs = self._attrs(line)
                name = line.split(",", 1)[1].strip() if "," in line else "Unnamed Channel"
                pending = (name, attrs.get("group-title", "Uncategorized"), attrs.get("tvg-logo", DEFAULT_LOGO), attrs)
            elif line.lower().startswith(("http://", "https://")) and pending:
                name, group, logo, attrs = pending
                self.add(name, line, group, logo, source,
                         {"attributes": attrs, "type": self.detect_type(line)})
                pending = None

    def parse_json(self, text: str, source: str):
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return False
        if isinstance(data, dict):
            for key in ("channels", "items", "data", "streams", "results"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
        if not isinstance(data, list):
            return False
        found = False
        for item in data:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("stream_url") or item.get("streamUrl") or item.get("link") or item.get("stream")
            if not isinstance(url, str):
                continue
            self.add(str(item.get("name") or item.get("title") or item.get("channel") or "Unnamed Channel"), url,
                     str(item.get("group") or item.get("group-title") or item.get("category") or "Uncategorized"),
                     str(item.get("logo") or item.get("img") or item.get("tvg-logo") or item.get("image") or DEFAULT_LOGO),
                     source, {"type": self.detect_type(url)})
            found = True
        return found

    def parse_html(self, text: str, source: str):
        parser = _LinkParser()
        parser.feed(text)
        for href in parser.links:
            url = urljoin(source, href)
            low = url.lower()
            path = urlparse(url).path.lower()
            if any(x in low for x in ("telegram", "login", "signup")):
                continue
            if path.endswith((".m3u", ".m3u8", ".mpd", ".mp4", ".ts")) or any(x in low for x in ("playlist", "stream")):
                self.add(os.path.basename(path) or "Stream", url, "Uncategorized", DEFAULT_LOGO, source,
                         {"type": self.detect_type(url)})

    @staticmethod
    def detect_type(url: str) -> str:
        path = urlparse(url).path.lower()
        if path.endswith(".m3u8"):
            return "hls"
        if path.endswith(".mpd"):
            return "dash"
        if path.endswith((".mp4", ".m4v", ".ts", ".mkv", ".webm")):
            return "media"
        return "unknown"

    def process_sources(self, sources: list[str]):
        for source in sources:
            text, final_url = self.fetch(source)
            if not text:
                continue
            lower = final_url.lower().split("?", 1)[0]
            parsed = False
            if lower.endswith(".json") or text.lstrip().startswith(("{", "[")):
                parsed = self.parse_json(text, final_url)
            if not parsed and "#EXTINF" in text[:30000]:
                self.parse_m3u(text, final_url)
                parsed = True
            if not parsed and lower.endswith((".html", ".htm")):
                self.parse_html(text, final_url)
            elif not parsed:
                self.parse_m3u(text, final_url)
        if self.check_links:
            self.validate()
        return self.channels

    @classmethod
    def _check(cls, url: str, timeout: float):
        try:
            r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code < 400:
                ct = (r.headers.get("content-type") or "").lower()
                if url.lower().split("?", 1)[0].endswith(".m3u8"):
                    return cls._check_hls(url, timeout, r.url)
                return True, r.url, r.status_code, ct
        except requests.RequestException:
            pass

        try:
            with requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True) as r:
                ct = (r.headers.get("content-type") or "").lower()
                if r.status_code >= 400:
                    return False, r.url, r.status_code, ct
                path = url.lower().split("?", 1)[0]
                if path.endswith(".m3u8"):
                    return cls._check_hls_response(r, timeout)
                if path.endswith(".mpd"):
                    chunk = next(r.iter_content(chunk_size=16384), b"")
                    valid = b"<MPD" in chunk or b":MPD" in chunk
                    return valid or "dash" in ct, r.url, r.status_code, ct
                return True, r.url, r.status_code, ct
        except requests.RequestException:
            return False, url, 0, ""

    @classmethod
    def _check_hls(cls, url: str, timeout: float, final_url: str):
        try:
            with requests.get(final_url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True) as r:
                return cls._check_hls_response(r, timeout)
        except requests.RequestException:
            return False, final_url, 0, ""

    @classmethod
    def _check_hls_response(cls, r, timeout: float):
        ct = (r.headers.get("content-type") or "").lower()
        sample_lines = []
        for line in r.iter_lines(decode_unicode=False):
            if line:
                sample_lines.append(line[:4096])
            if len(sample_lines) >= 24:
                break
        manifest = b"\n".join(sample_lines).upper()
        if not (b"#EXTM3U" in manifest or "mpegurl" in ct):
            return False, r.url, r.status_code, ct
        segment = next((x.decode("utf-8", "ignore").strip() for x in sample_lines
                        if not x.startswith(b"#") and x.strip()), "")
        if not segment:
            return True, r.url, r.status_code, ct
        child = urljoin(r.url, segment)
        try:
            with requests.get(child, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True) as probe:
                if probe.status_code >= 400:
                    return False, r.url, r.status_code, ct
                chunk = next(probe.iter_content(chunk_size=2048), b"")
                return bool(chunk), r.url, r.status_code, ct
        except requests.RequestException:
            return False, r.url, r.status_code, ct

    def validate(self):
        kept = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._check, ch["url"], self.timeout): ch for ch in self.channels}
            for future in concurrent.futures.as_completed(futures):
                ch = futures[future]
                try:
                    ok, final_url, status, ct = future.result()
                    if ok:
                        ch["url"] = normalize_url(final_url)
                        ch["status"] = "active"
                        ch["http_status"] = status
                        ch["content_type"] = ct
                        kept.append(ch)
                except Exception as exc:
                    LOG.debug("Validation error for %s: %s", ch["url"], exc)
        self.channels = kept
        return kept

    @staticmethod
    def _m3u_attr(value: str) -> str:
        """Escape a value used inside an EXTINF quoted attribute."""
        return str(value).replace('"', "&quot;").replace("\n", " ").replace("\r", " ")

    @staticmethod
    def _m3u_name(value: str) -> str:
        """Escape a display name (playlist injection guard for hostile upstreams)."""
        return str(value).replace("\n", " ").replace("\r", " ")

    def export(self):
        grouped = defaultdict(list)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        for ch in self.channels:
            grouped[ch["group"]].append(ch)
        payload = {"updated": now, "country": self.country, "count": len(self.channels), "channels": dict(grouped)}
        with open(os.path.join(self.output_dir, f"{self.file_prefix}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(os.path.join(self.output_dir, self.file_prefix), "w", encoding="utf-8") as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)
        with open(os.path.join(self.output_dir, f"{self.file_prefix}.m3u"), "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in self.channels:
                logo = self._m3u_attr(ch["logo"])
                group = self._m3u_attr(ch["group"])
                name = self._m3u_name(ch["name"])
                f.write(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group}",{name}\n{ch["url"]}\n')
        with open(os.path.join(self.output_dir, f"{self.file_prefix}.txt"), "w", encoding="utf-8") as f:
            for ch in self.channels:
                f.write(f'{ch["name"]} | {ch["group"]} | {ch["url"]}\n')
