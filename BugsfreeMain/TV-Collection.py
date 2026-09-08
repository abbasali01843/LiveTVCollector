"""Collection source collector using the shared collector core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/iptv-ch/iptv-ch.github.io/refs/heads/master/webtv.m3u",
    "https://github.com/iptv-ch/iptv-ch.github.io/raw/refs/heads/master/netplus.m3u8",
]


def main():
    collector = Collector(country="Collection", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
