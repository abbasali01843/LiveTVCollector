from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/LITUATUI/M3UPT/main/M3U/M3UPT.m3u",
    "https://iptv-org.github.io/iptv/countries/pt.m3u",
    "https://raw.githubusercontent.com/inspirationlinks/m3u/refs/heads/live/Freetv.m3u",
]


def main():
    collector = Collector(country="Portugal", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
