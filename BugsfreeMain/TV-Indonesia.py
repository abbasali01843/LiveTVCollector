from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/djonyttnt/mytvnet/refs/heads/main/nonton",
    "https://raw.githubusercontent.com/moasisantonio/Moasis/refs/heads/main/moasisantonio.m3u",
    "https://raw.githubusercontent.com/denimaung/nontontv/refs/heads/main/playlist.M3U",
    "https://raw.githubusercontent.com/okasahisnu/IPTV/refs/heads/main/Main",
    "https://raw.githubusercontent.com/alkhalifitv/TV/refs/heads/master/playlist",
    "https://raw.githubusercontent.com/ojiwzrd10/iptv/refs/heads/main/id.json",
    "https://raw.githubusercontent.com/abidinrj/nontontv/refs/heads/main/playlist",
    "https://raw.githubusercontent.com/KiTVNoSignaL/PlayList/refs/heads/main/NoSignaL",
    "https://raw.githubusercontent.com/emonnaja/Indonesian-IPTV/refs/heads/main/index.m3u",
    "https://iptv-org.github.io/iptv/countries/id.m3u",
]


def main():
    collector = Collector(country="Indonesia", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
