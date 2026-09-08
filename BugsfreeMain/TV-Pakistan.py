from BugsfreeCore.collector import Collector

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/pk.m3u",
    "https://raw.githubusercontent.com/tat2027/a/refs/heads/main/pk",
]


def main():
    collector = Collector(country="Pakistan", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
