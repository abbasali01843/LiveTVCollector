from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/RokuIL/Live-From-Israel/master/Channels.json",
    "https://raw.githubusercontent.com/phamanhquan2001/IPTV/refs/heads/main/Conflict%20Zone.m3u",
    "https://iptv-org.github.io/iptv/countries/il.m3u",
]


def main():
    collector = Collector(country="Israel", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
