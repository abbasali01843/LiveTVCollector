from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/MIFNtechnology/siaranMy/refs/heads/main/myIPtv.m3u8",
    "https://raw.githubusercontent.com/hazrulamin/iptv/refs/heads/main/iptv.m3u",
    "https://iptv-org.github.io/iptv/countries/my.m3u",
]


def main():
    collector = Collector(country="Malaysia", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
