from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/kupjta/iptv/refs/heads/main/kupjtv.m3u",
    "https://raw.githubusercontent.com/bestcommt2/iptv/refs/heads/master/fuckidplus.w3u",
    "https://iptv-org.github.io/iptv/countries/th.m3u",
]


def main():
    collector = Collector(country="Thailand", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
