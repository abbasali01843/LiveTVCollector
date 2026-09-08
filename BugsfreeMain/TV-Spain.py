from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/ahmedkassem2004/M3U-player/refs/heads/main/playlist.m3u",
    "https://raw.githubusercontent.com/Sunstar16/FULL-IPTV-CHANNEL-PLAYLIST/refs/heads/main/Main%20Necessary%20Channels.m3u",
    "https://iptv-org.github.io/iptv/countries/es.m3u",
]


def main():
    collector = Collector(country="Spain", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
