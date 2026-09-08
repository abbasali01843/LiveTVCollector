from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_CA.m3u",
    "https://iptv-org.github.io/iptv/countries/ca.m3u",
]


def main():
    collector = Collector(country="Canada", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
