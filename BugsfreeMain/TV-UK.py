from BugsfreeCore.collector import Collector


SOURCES = [
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_GB.m3u",
    "https://iptv-org.github.io/iptv/countries/uk.m3u",
]


def main():
    collector = Collector(country="UK", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Collected {len(collector.channels)} unique channels for UK")


if __name__ == "__main__":
    main()
