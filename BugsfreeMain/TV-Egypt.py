from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/waheeb1983/iptv-player/master/Channels/merged_playlist.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
]


def main():
    collector = Collector(country="Egypt", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
