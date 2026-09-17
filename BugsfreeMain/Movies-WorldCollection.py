"""World movie collection using the shared collector core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/PuteraPerlis74/Tv/refs/heads/main/MY%20FILM",
    "https://raw.githubusercontent.com/PuteraPerlis74/Tv/refs/heads/main/My%20Film",
]


def main():
    collector = Collector(country="WorldCollection", base_dir="Movies", file_prefix="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"WorldCollection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
