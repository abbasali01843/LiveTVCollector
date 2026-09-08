from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/ARAB-IPTV/ARAB-IPTV/main/ARABIPTV.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
]


def main():
    collector = Collector(country="Arabic", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
