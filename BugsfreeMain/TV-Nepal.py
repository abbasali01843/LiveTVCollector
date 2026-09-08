from BugsfreeCore.collector import Collector

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/np.m3u",
]


def main():
    collector = Collector(country="Nepal", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
