from BugsfreeCore.collector import Collector

SOURCES = [
    "https://iptv-org.github.io/iptv/countries/pe.m3u",
    "https://raw.githubusercontent.com/antholyber1a/lista-iptv-peru/refs/heads/main/iptvperu.m3u",
    "https://raw.githubusercontent.com/jesaro15/iptv/refs/heads/main/play.m3u",
]


def main():
    collector = Collector(country="Peru", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
