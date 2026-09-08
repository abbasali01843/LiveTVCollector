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
from urllib.parse import urljoin, urlparse

import requests

LOG = logging.getLogger(__name__)

DEFAULT_LOGO = "https://bugsfreeweb.github.io/LiveTVCollector/BugsfreeLogo/default-logo.png"
HEADERS = {"User-Agent": "LiveTVCollector/2.0 (+https://github.com/abbasali01843/LiveTVCollector)"}


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


class Collector:
    def __init__(self, country: str, base_dir: str = "LiveTV", check_links: bool = False,
                 max_workers: int = 20, timeout: float = 8):
        self.country = country
        self.output_dir = os.path.join(base_dir, country)
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
        url = url.strip()
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
                pending = (name, attrs.get("group-title", "Uncategorized"),
                           attrs.get("tvg-logo", DEFAULT_LOGO), attrs)
            elif line.lower().startswith(("http://", "https://")) and pending:
                name, group, logo, attrs = pending
                self.add(name, line, group, logo, source, {"attributes": attrs})
                pending = None

    def parse_json(self, text: str, source: str):
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return False
        if isinstance(data, dict):
            data = data.get("channels", data.get("items", data.get("data", [])))
        if not isinstance(data, list):
            return False
        count = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("stream_url") or item.get("streamUrl") or item.get("link")
            if not isinstance(url, str):
                continue
            self.add(str(item.get("name") or item.get("title") or "Unnamed Channel"), url,
                     str(item.get("group") or item.get("group-title") or item.get("category") or "Uncategorized"),
                     str(item.get("logo") or item.get("img") or item.get("tvg-logo") or DEFAULT_LOGO), source)
            count += 1
        return count > 0

    def parse_html(self, text: str, source: str):
        parser = _LinkParser()
        parser.feed(text)
        for href in parser.links:
            url = urljoin(source, href)
            path = urlparse(url).path.lower()
            if any(x in url.lower() for x in ("telegram", "login", "signup")):
                continue
            if path.endswith((".m3u", ".m3u8", ".mpd", ".mp4", ".ts")) or any(x in url.lower() for x in ("playlist", "stream")):
                self.add(os.path.basename(path) or "Stream", url, "Uncategorized", DEFAULT_LOGO, source)

    def process_sources(self, sources: list[str]):
        for source in sources:
            text, final_url = self.fetch(source)
            if not text:
                continue
            lower = final_url.lower().split("?", 1)[0]
            parsed = False
            if lower.endswith(".json"):
                parsed = self.parse_json(text, final_url)
            if not parsed and (text.lstrip().startswith("{") or text.lstrip().startswith("[")):
                parsed = self.parse_json(text, final_url)
            if not parsed and "#EXTINF" in text[:20000]:
                self.parse_m3u(text, final_url)
                parsed = True
            if not parsed and lower.endswith((".html", ".htm")):
                self.parse_html(text, final_url)
            elif not parsed:
                # Last attempt: many raw playlist files have no useful extension.
                self.parse_m3u(text, final_url)
        if self.check_links:
            self.validate()
        return self.channels

    @staticmethod
    def _check(url: str, timeout: float):
        try:
            r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code < 400:
                return True, r.url
        except requests.RequestException:
            pass
        try:
            with requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True, stream=True) as r:
                if r.status_code >= 400:
                    return False, url
                content_type = (r.headers.get("content-type") or "").lower()
                if url.lower().split("?", 1)[0].endswith(".m3u8"):
                    sample = next(r.iter_lines(), b"")
                    return b"#EXTM3U" in sample.upper() or "mpegurl" in content_type, r.url
                return True, r.url
        except requests.RequestException:
            return False, url

    def validate(self):
        LOG.info("Validating %d streams", len(self.channels))
        kept = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._check, ch["url"], self.timeout): ch for ch in self.channels}
            for future in concurrent.futures.as_completed(futures):
                ch = futures[future]
                try:
                    ok, final_url = future.result()
                    if ok:
                        ch["url"] = final_url
                        ch["status"] = "active"
                        kept.append(ch)
                except Exception as exc:
                    LOG.debug("Validation error for %s: %s", ch["url"], exc)
        self.channels = kept
        return kept

    def export(self):
        grouped = defaultdict(list)
        for ch in self.channels:
            grouped[ch["group"]].append(ch)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        payload = {"updated": now, "country": self.country, "count": len(self.channels), "channels": dict(grouped)}
        with open(os.path.join(self.output_dir, "LiveTV.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        with open(os.path.join(self.output_dir, "LiveTV"), "w", encoding="utf-8") as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)
        with open(os.path.join(self.output_dir, "LiveTV.m3u"), "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for ch in self.channels:
                f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}\n{ch["url"]}\n')
        with open(os.path.join(self.output_dir, "LiveTV.txt"), "w", encoding="utf-8") as f:
            for ch in self.channels:
                f.write(f'{ch["name"]} | {ch["group"]} | {ch["url"]}\n')
