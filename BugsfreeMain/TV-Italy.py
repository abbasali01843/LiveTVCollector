from BugsfreeCore.collector import Collector

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/it.m3u",
    "https://raw.githubusercontent.com/gRullo/italym3u/refs/heads/main/italy.m3u",
    "https://raw.githubusercontent.com/kiekostui/IPTV/refs/heads/main/playlist.m3u8",
    "https://raw.githubusercontent.com/pandvan/rakuten-m3u-generator/refs/heads/master/output/rakuten.m3u",
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_IT.m3u",
]


def main():
    collector = Collector(country="Italy", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
