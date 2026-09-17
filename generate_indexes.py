"""Generate compact, data-aware indexes for LiveTV, Movies and SpecialLinks outputs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Categories quarantined as adult-only (18+). They stay in the repo but are
# explicitly flagged so clients can filter them out.
ADULT_CATEGORIES = {
    "Movies/Private",
    "SpecialLinks/ADULTS_ONLY",
}


def read_count(folder: Path) -> int:
    for name in ("LiveTV.json", "Movies.json"):
        path = folder / name
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("count"), int):
                    return data["count"]
                if isinstance(data, dict) and isinstance(data.get("channels"), dict):
                    return sum(len(v) for v in data["channels"].values() if isinstance(v, list))
                if isinstance(data, list):
                    return len(data)
            except (OSError, json.JSONDecodeError):
                pass
    return 0


def read_special_count(folder: Path) -> tuple[int, list[str]]:
    """Count SpecialLinks entries (SpecialLinks*.json across country subdirs)."""
    total = 0
    countries: list[str] = []
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        countries.append(sub.name)
        for path in sorted(sub.glob("SpecialLinks*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    total += len(data)
            except (OSError, json.JSONDecodeError):
                pass
    return total, countries


def health_summary(folder_name: str, health_path: Path) -> dict:
    if not health_path.exists():
        return {}
    try:
        data = json.loads(health_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    # Preferred: per-country table computed over ALL channels (dedup-aware).
    table = data.get("country_health")
    if isinstance(table, dict) and isinstance(table.get(folder_name), dict):
        row = table[folder_name]
        return {
            "checked": int(row.get("total", 0)),
            "active": int(row.get("active", 0)),
            "geo_or_restricted": int(row.get("geo_or_restricted", 0)),
            "down": int(row.get("down", 0)),
            "timeout": int(row.get("timeout", 0)),
            "unknown": int(row.get("unknown", 0)),
            "invalid": int(row.get("invalid", 0)),
            "average_score": row.get("average_score", 0),
            "checked_at": data.get("updated"),
        }
    # Fallback: filter the unique-stream list (legacy health.json files).
    streams = [x for x in data.get("streams", []) if isinstance(x, dict)]
    streams = [x for x in streams if x.get("country") == folder_name]
    if not streams:
        return {}
    statuses: dict[str, int] = {}
    for item in streams:
        status = str(item.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
    scores = [int(item.get("score", 0)) for item in streams if isinstance(item.get("score", 0), (int, float))]
    return {
        "checked": len(streams),
        "active": statuses.get("active", 0),
        "geo_or_restricted": statuses.get("geo_or_restricted", 0),
        "down": statuses.get("down", 0),
        "timeout": statuses.get("timeout", 0),
        "unknown": statuses.get("unknown", 0),
        "invalid": statuses.get("invalid", 0),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "checked_at": data.get("updated"),
    }


def generate_index(root: str) -> None:
    base = Path(root)
    if not base.exists():
        return
    health_path = Path("BugsfreeStreams/Output/health.json") if root == "LiveTV" else Path("__missing_health.json")
    entries = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        entry = {
            "name": folder.name,
            "count": read_count(folder),
            "path": str(folder.relative_to(base)),
            "files": sorted(p.name for p in folder.iterdir() if p.is_file()),
        }
        if f"{root}/{folder.name}" in ADULT_CATEGORIES:
            entry["content_warning"] = "adult-only-18+"
        health = health_summary(folder.name, health_path)
        if health:
            entry["health"] = health
        entries.append(entry)
    payload = {
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "count": len(entries),
        "items": entries,
    }
    (base / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_special_index(root: str = "SpecialLinks") -> None:
    base = Path(root)
    if not base.exists():
        return
    entries = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        count, countries = read_special_count(folder)
        entry: dict = {
            "name": folder.name,
            "count": count,
            "path": str(folder.relative_to(base)),
            "countries": countries,
        }
        if f"{root}/{folder.name}" in ADULT_CATEGORIES:
            entry["content_warning"] = "adult-only-18+"
        entries.append(entry)
    payload = {
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "count": len(entries),
        "total_entries": sum(e["count"] for e in entries),
        "items": entries,
    }
    (base / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate_index("LiveTV")
    generate_index("Movies")
    generate_special_index("SpecialLinks")
