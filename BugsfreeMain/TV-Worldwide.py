"""Worldwide source collector using the shared collector core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/zking2000/m3u/refs/heads/main/working_streams.m3u",
    "https://raw.githubusercontent.com/iprtl/m3u/live/Freetv.m3u",
    "https://raw.githubusercontent.com/YueChan/Live/main/Global.m3u",
    "https://raw.githubusercontent.com/ipstreet312/freeiptv/refs/heads/master/all.m3u",
    "https://raw.githubusercontent.com/gambiarras/legal-iptv/refs/heads/main/playlist.m3u",
    "https://raw.githubusercontent.com/Novantama/IPTV/refs/heads/Main/Playlist/AllWorld.m3u",
    "https://raw.githubusercontent.com/altn2025/iptv/refs/heads/main/international.m3u",
]


def main():
    collector = Collector(country="Worldwide", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
