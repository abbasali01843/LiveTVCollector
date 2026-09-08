"""Bollywood movie source collector using the shared core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/Mahabubulalammim/New/refs/heads/main/Mim%20New%20Movie%20Collection",
    "https://raw.githubusercontent.com/Mahabubulalammim/New/refs/heads/main/Mim-Movies.mim",
]


def main():
    collector = Collector(country="Bollywood", base_dir="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Bollywood collection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
