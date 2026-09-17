"""SpecialExcess collector using the shared collector core.

NOTE: only M3U sources are supported; the legacy .w3u mirrors were dropped
because neither the old nor the new parser understands that format.
"""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/HelmerLuzo/RakutenTV_HL/refs/heads/main/tv/m3u/RakutenTV_tv.m3u",
    "https://raw.githubusercontent.com/HelmerLuzo/CanelaTV_HL/refs/heads/main/tv/m3u/CanelaTV_tv.m3u",
    "https://raw.githubusercontent.com/HelmerLuzo/RuntimeTV_HL/refs/heads/main/tv/m3u/RuntimeTV_tv.m3u",
]


def main():
    collector = Collector(country="SpecialExcess", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Collected {len(collector.channels)} unique channels for SpecialExcess")


if __name__ == "__main__":
    main()
