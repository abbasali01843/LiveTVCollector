"""VOD collector using the shared LiveTVCollector parser/validator.

Sources are intentionally configuration-driven. Put one or more public/legal
M3U/JSON URLs in MOVIES_VOD_SOURCES (newline/comma separated) when a source is
available. The workflow does not contain private credentials or Xtream URLs.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from BugsfreeCore.collector import Collector

DEFAULT_SOURCES = [
    # Public Pluto VOD playlist mirror. This file can be empty when the upstream
    # region currently publishes no VOD entries; the collector handles that safely.
    "https://raw.githubusercontent.com/OwnerPlugins/pluto-tv-m3u/main/pluto-vod-US.m3u",
]


def sources() -> list[str]:
    raw = os.getenv("MOVIES_VOD_SOURCES", "")
    configured = [x.strip() for x in raw.replace(",", "\n").splitlines() if x.strip()]
    return configured or DEFAULT_SOURCES


def main() -> None:
    collector = Collector(country="VOD", base_dir="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(sources())
    collector.export()

    out = Path("Movies/VOD")
    mapping = {
        "LiveTV.m3u": "Movies.m3u",
        "LiveTV.txt": "Movies.txt",
        "LiveTV.json": "Movies.json",
        "LiveTV": "Movies",
    }
    for src, dst in mapping.items():
        src_path = out / src
        dst_path = out / dst
        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))

    print(f"VOD collection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
