"""Generate compact, data-aware indexes for LiveTV and Movies outputs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


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


def generate_index(root: str) -> None:
    base = Path(root)
    if not base.exists():
        return
    entries = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        entries.append({
            "name": folder.name,
            "count": read_count(folder),
            "path": str(folder.relative_to(base)),
            "files": sorted(p.name for p in folder.iterdir() if p.is_file()),
        })
    payload = {
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "count": len(entries),
        "items": entries,
    }
    (base / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate_index("LiveTV")
    generate_index("Movies")
