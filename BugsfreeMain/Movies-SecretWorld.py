"""SecretWorld movie collector using the shared core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/gluk03/iptvgluk/refs/heads/main/tizam.m3u",
    "https://raw.githubusercontent.com/gluk03/iptvgluk/refs/heads/main/TV.m3u",
]


def main():
    collector = Collector(country="SecretWorld", base_dir="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"SecretWorld collection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
