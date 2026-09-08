from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/Efeisot/iptv/refs/heads/main/index.m3u",
    "https://raw.githubusercontent.com/ilyswch/IPTV-TR/refs/heads/main/index.m3u",
    "https://raw.githubusercontent.com/ilyswch/IPTV-TR/refs/heads/main/box.m3u",
    "https://raw.githubusercontent.com/ilyswch/IPTV-TR/refs/heads/main/box2.m3u",
    "https://iptv-org.github.io/iptv/countries/tr.m3u",
]


def main():
    collector = Collector(country="Turkey", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
