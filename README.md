# LiveTVCollector

Automated collection, normalization, health checking, and export of publicly available live-TV stream metadata.

> This repository aggregates publicly available stream links. It does not host or transmit video content. Use only sources and streams you are legally permitted to access.

## Content notice (quarantine)

Two collections are flagged **adult-only (18+)** and kept for archival purposes:

- `Movies/Private` — upstream sources are explicitly adult IPTV lists.
- `SpecialLinks/ADULTS_ONLY` — adult group from the special collection.

Both carry `"content_warning": "adult-only-18+"` in the generated indexes (`Movies/index.json`, `SpecialLinks/index.json`) and are badged in the web hub, so clients can filter them out. Do not add new adult sources. If your use-case cannot include adult metadata at all, ignore these two paths.

## Architecture

```text
Country / category sources
        ↓
BugsfreeCore/collector.py          (shared: M3U · JSON · HTML · HLS/DASH refs)
        ↓
Normalized channel records        (BugsfreeMain/*, one thin file per country)
        ↓
BugsfreeStreams/validator.py       (redirects · HLS/DASH/media probes · scoring)
        ↓
Deduplication + per-country health (country_health table)
        ↓
JSON · M3U · TXT · app-ready datasets + indexes
```

Live site: `https://abbasali01843.github.io/LiveTVCollector/` (`index.html`).

## Core components

### Unified collector

`BugsfreeCore/collector.py` is shared by **all** country/category collectors in `BugsfreeMain/`. It normalizes URLs and channel metadata, supports M3U/JSON/HTML sources, detects common stream protocols, removes duplicates, escapes playlist output, and writes the standard exports (file prefix `LiveTV` or `Movies`).

### Unified health validator

`BugsfreeStreams/validator.py` scans the generated `LiveTV/*/LiveTV.json` datasets and performs concurrent health checks (per-host throttling). It handles redirects and recognizes HLS (`.m3u8`), DASH (`.mpd`), and direct media URLs, probing manifests *and* sample segments.

Health results are written to:

- `BugsfreeStreams/Output/health.json` — detailed stream health data incl. `country_health`.
- `BugsfreeStreams/Output/active.json` — active streams across countries.
- `BugsfreeStreams/Output/active.m3u` — active streams as a standard playlist.
- `BugsfreeStreams/Output/countries/<country>.json` — active streams for one country.
- `BugsfreeStreams/Output/countries/<country>.m3u` — country playlist.
- `BugsfreeStreams/Output/countries.json` — country-level summary.
- `BugsfreeStreams/Output/manifest.json` — machine-readable output manifest.

`generate_indexes.py` enriches `LiveTV/index.json` with these per-country summaries (dedup-aware via `country_health`), flags adult collections, and builds `Movies/index.json` + `SpecialLinks/index.json`.

### Standard exports

Each collector writes these files under `LiveTV/<Country>/` (or `Movies/<Category>/` with the `Movies` prefix):

- `LiveTV.json` — structured channel data (`updated`, `country`, `count`, grouped `channels`).
- `LiveTV.m3u` — standard M3U playlist.
- `LiveTV.txt` — readable channel listing.
- `LiveTV` — extensionless JSON export for clients that expect the historical format.

## Supported source formats

The shared collector can consume:

- M3U / M3U8 playlists
- JSON channel lists
- HTML pages containing stream URLs
- HLS references
- DASH/MPD references
- common direct-media URLs

Source-specific collectors define their public source URLs in `BugsfreeMain/`.

## GitHub Actions

Collector schedules are staggered (minutes `0–36` at `00:00/08:00/16:00 UTC`) and serialized through the `collector-main` concurrency group so writers never race each other; every writer rebases before pushing.

### Unified stream health

`.github/workflows/health-validator.yml` is the **single** validator: twice-daily schedule plus manual execution. It rebuilds `BugsfreeStreams/Output/` and all three indexes. (The old duplicate `validate-streams.yml` was removed.)

### Repository quality

`.github/workflows/quality.yml` runs on pushes, pull requests, and manual execution. It compiles the Python sources and runs both the collector and validator unit tests.

### Special collection

`SpecialCollection.js` consumes additional public/legal M3U or JSON sources supplied through the `SPECIAL_M3U_URLS` secret, honoring the dependency-free settings in `config.yml`. The scheduled workflow is safe when that secret is absent and simply skips the collection. Committed `SpecialLinks/` data cannot be reproduced without that secret.

### Movies VOD

The VOD collector uses the same shared collector infrastructure. Additional source URLs can be supplied through `MOVIES_VOD_SOURCES`. Only sources that are publicly available and legally usable should be configured.

### Legacy (retired)

`BugsfreeStreams/process_streams-*.py` + the 17 `Stream_checker-*.yml` workflows are deprecated and **manual-only**. Their `Output/StreamLinks-*.m3u`, `StreamsTV-*` wrappers, and `processed_links-*.json` caches are frozen historical artifacts — do not build new integrations on them.

## Local development

Requirements:

- Python 3.11+
- Node.js 20+ only for the optional SpecialCollection workflow
- Python dependency: `requests`

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the quality checks:

```bash
python -m compileall -q BugsfreeCore BugsfreeMain BugsfreeStreams
python -m unittest discover -s BugsfreeCore/tests -p 'test_*.py' -v
python -m unittest discover -s BugsfreeStreams/tests -p 'test_*.py' -v
```

Run a collector directly:

```bash
python BugsfreeMain/TV-Bangladesh.py
```

Run the unified health validator after country datasets have been generated:

```bash
python BugsfreeStreams/validator.py
python generate_indexes.py
```

Check the JS collector syntax:

```bash
node --check SpecialCollection.js
```

## Adding or updating sources

Add or replace source URLs in the relevant collector under `BugsfreeMain/`. Prefer stable, public, legal sources. Avoid putting credentials, private URLs, access tokens, or other secrets in tracked files. If a URL contains an access token (e.g. `...&token=...`), treat it as access-controlled and do not commit it.

For sources that need credentials or private configuration, use GitHub Actions secrets and keep the tracked configuration empty of sensitive values.

## Data quality notes

A reachable HTTP URL is not automatically a playable stream. The validator therefore treats HLS and DASH manifests differently from ordinary HTTP endpoints and assigns a health score/status based on the probe result.

Transient network failures can occur because of rate limits, geo restrictions, source outages, or upstream changes. Generated health data should therefore be treated as a point-in-time snapshot rather than a permanent guarantee.

Known weak datasets: `LiveTV/SpecialExcess` and `Movies/VOD` currently collect zero entries (dead/empty upstreams); `Movies/WorldCollection`, `LiveTV/Malaysia`, and `LiveTV/Nepal` are very small. Contributions of reliable replacements are welcome.

## Contributing

Useful contributions include:

- adding reliable public/legal sources;
- improving parser compatibility;
- improving stream-health detection;
- adding tests for new source formats;
- improving app/client export compatibility.

Please avoid committing credentials, tokenized URLs, or private stream URLs.

## License

This project is released under the MIT License. See `LICENSE`.

## Disclaimer

This project is an aggregation and research utility. It does not host, transmit, or claim ownership of third-party streaming content. Stream availability, authorization, copyright status, and terms of use belong to the respective source/provider. Users are responsible for complying with applicable law and source terms.
