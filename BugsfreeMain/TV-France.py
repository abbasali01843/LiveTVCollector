from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/ipstreet312/freeiptv/refs/heads/master/all.m3u",
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_FR.m3u",
    "https://iptv-org.github.io/iptv/countries/fr.m3u",
]


def main():
    collector = Collector(country="France", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
