"""Hollywood movie source collector using the shared core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Marvel",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Fantas%C3%ADa",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Max",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Neflix",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Paramount",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Romance",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Star",
    "https://raw.githubusercontent.com/BrianRVP/Bflix34567/refs/heads/main/Terror",
]


def main():
    collector = Collector(country="Hollywood", base_dir="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Hollywood collection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
