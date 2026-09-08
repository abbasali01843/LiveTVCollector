"""Private movie collector using the shared core.

CONTENT NOTICE: the upstream sources below are adult-only (18+). They are
kept for archival/quarantine purposes and are flagged with a content warning
in the generated indexes. Do not add new adult sources here.
"""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://adultiptv.net/chs.m3u",
    "https://raw.githubusercontent.com/3thAn9u/yang-m3u/refs/heads/main/A.m3u",
    "https://raw.githubusercontent.com/denisskashin/iptv/refs/heads/main/xxx.m3u",
    "https://raw.githubusercontent.com/kupjta/iptv/refs/heads/main/18plus.m3u",
]


def main():
    collector = Collector(country="Private", base_dir="Movies", file_prefix="Movies",
                          check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Private collection complete: {len(collector.channels)} entries")


if __name__ == "__main__":
    main()
