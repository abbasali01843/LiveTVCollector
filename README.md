# LiveTVCollector

Automated collection, normalization, health checking, and export of publicly available live-TV stream metadata.

> This repository aggregates publicly available stream links. It does not host or transmit video content. Use only sources and streams you are legally permitted to access.

## Architecture

```text
Country / category sources
        ↓
BugsfreeCore/collector.py
  M3U · JSON · HTML · M3U8/MPD references
        ↓
Normalized channel records
        ↓
BugsfreeStreams/validator.py
  redirects · HLS · DASH · media · health scoring
        ↓
Deduplication + active-stream filtering
        ↓
JSON · M3U · TXT · app-ready datasets
```

## Core components

### Unified collector

`BugsfreeCore/collector.py` is shared by the country/category collectors. It normalizes URLs and channel metadata, supports M3U/JSON/HTML sources, detects common stream protocols, removes duplicates, and writes the standard country exports.

Collectors live under `BugsfreeMain/` and use the same core instead of maintaining separate implementations of the parser and validator.

### Unified health validator

`BugsfreeStreams/validator.py` scans the generated `LiveTV/*/LiveTV.json` datasets and performs concurrent health checks. It handles redirects and recognizes HLS (`.m3u8`), DASH (`.mpd`), and direct media URLs.

Health results are written to:

- `BugsfreeStreams/Output/health.json` — detailed stream health data.
- `BugsfreeStreams/Output/active.json` — active streams across countries.
- `BugsfreeStreams/Output/active.m3u` — active streams as a standard playlist.
- `BugsfreeStreams/Output/countries/<country>.json` — active streams for one country.
- `BugsfreeStreams/Output/countries/<country>.m3u` — country playlist.
- `BugsfreeStreams/Output/countries.json` — country-level summary.
- `BugsfreeStreams/Output/manifest.json` — machine-readable output manifest.

`generate_indexes.py` also enriches `LiveTV/index.json` with health summaries when health data is available.

## Standard country exports

Each collector normally writes these files under `LiveTV/<Country>/`:

- `LiveTV.json` — structured channel data.
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

The repository uses GitHub Actions for collection, validation, indexing, and quality checks.

### Unified stream health

`.github/workflows/health-validator.yml` runs the unified validator on a twice-daily schedule and supports manual execution. It uses the `collector-main` concurrency group so generated-data writers do not intentionally run against each other at the same time.

### Repository quality

`.github/workflows/quality.yml` runs on pushes, pull requests, and manual execution. It compiles the Python sources and runs both the collector and validator unit tests.

### Special collection

`SpecialCollection.js` can consume additional public/legal M3U or JSON sources supplied through the `SPECIAL_M3U_URLS` GitHub Actions secret. The scheduled workflow is safe when that secret is absent and simply skips the collection.

### Movies VOD

The optional VOD collector uses the same shared collector infrastructure. Additional source URLs can be supplied through `MOVIES_VOD_SOURCES`. Only sources that are publicly available and legally usable should be configured.

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

## Adding or updating sources

Add or replace source URLs in the relevant collector under `BugsfreeMain/`. Prefer stable, public, legal sources. Avoid putting credentials, private URLs, access tokens, or other secrets in tracked files.

For sources that need credentials or private configuration, use GitHub Actions secrets and keep the tracked configuration empty of sensitive values.

## Data quality notes

A reachable HTTP URL is not automatically a playable stream. The validator therefore treats HLS and DASH manifests differently from ordinary HTTP endpoints and assigns a health score/status based on the probe result.

Transient network failures can occur because of rate limits, geo restrictions, source outages, or upstream changes. Generated health data should therefore be treated as a point-in-time snapshot rather than a permanent guarantee.

## Contributing

Useful contributions include:

- adding reliable public/legal sources;
- improving parser compatibility;
- improving stream-health detection;
- adding tests for new source formats;
- improving app/client export compatibility.

Please avoid committing credentials or private stream URLs.

## License

This project is released under the MIT License. See `LICENSE`.

## Disclaimer

This project is an aggregation and research utility. It does not host, transmit, or claim ownership of third-party streaming content. Stream availability, authorization, copyright status, and terms of use belong to the respective source/provider. Users are responsible for complying with applicable law and source terms.
