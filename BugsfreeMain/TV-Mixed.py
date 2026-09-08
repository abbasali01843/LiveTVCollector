"""Mixed worldwide source collector using the shared collector core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/pandvan/rakuten-m3u-generator/master/output/rakuten.m3u",
    "https://raw.githubusercontent.com/LiveTvWorldwide/IPTV/refs/heads/main/live.m3u",
    "https://raw.githubusercontent.com/zagomedia/televizor/refs/heads/main/iptvlist.m3u",
    "https://raw.githubusercontent.com/demons-777/miptv/refs/heads/main/miptv",
    "https://raw.githubusercontent.com/PuteraPerlis74/Tv/refs/heads/main/MYTV.m3u",
    "https://raw.githubusercontent.com/phamanhquan2001/IPTV/refs/heads/main/Conflict%20Zone.m3u",
]


def main():
    collector = Collector(country="Mixed", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
