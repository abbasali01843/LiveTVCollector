from BugsfreeCore.collector import Collector


SOURCES = [
    "https://raw.githubusercontent.com/Arunjunan20/My-IPTV/refs/heads/main/index.html",
    "https://raw.githubusercontent.com/FunctionError/PiratesTv/main/combined_playlist.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u",
]


def main():
    collector = Collector(country="India", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Collected {len(collector.channels)} unique India channels")


if __name__ == "__main__":
    main()
