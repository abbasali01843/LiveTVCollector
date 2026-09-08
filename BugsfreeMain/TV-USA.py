from BugsfreeCore.collector import Collector


SOURCES = [
    "https://iptv-org.github.io/iptv/countries/us.m3u",
    "https://raw.githubusercontent.com/clseibold/tubi-m3u/refs/heads/main/tubi_playlist_us.m3u",
    "https://raw.githubusercontent.com/aceray50/iptv/refs/heads/main/tv.m3u",
    "https://raw.githubusercontent.com/pigzillaaaaa/iptv-scraper/refs/heads/main/thetvapp.m3u8",
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_US.m3u",
]


def main():
    collector = Collector(country="USA", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Collected {len(collector.channels)} unique USA channels")


if __name__ == "__main__":
    main()
