"""Worldwide movie collector using the shared collector core."""
from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/moasisantonio/Moasis/refs/heads/main/vodmoasisantonio.m3u",
    "https://raw.githubusercontent.com/Pibyto/pibytotv.m3u/refs/heads/main/ClaudioTV01",
    "https://raw.githubusercontent.com/denisskashin/iptv/refs/heads/main/movies.m3u",
    "https://raw.githubusercontent.com/denisskashin/iptv/refs/heads/main/rus_movies.m3u",
    "https://raw.githubusercontent.com/Buddyalfian25/nontons/refs/heads/main/VOD",
    "https://raw.githubusercontent.com/Buddyalfian25/nontons/refs/heads/main/V%20O%20D",
    "https://raw.githubusercontent.com/mimipipi22/lalajo/refs/heads/main/vod",
    "https://raw.githubusercontent.com/mimipipi22/lalajo/refs/heads/main/DewaNonton",
]


def main():
    collector = Collector(country="Worldwide", base_dir="Movies", check_links=True, max_workers=32, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Worldwide movie collection complete: {len(collector.channels)} active entries")


if __name__ == "__main__":
    main()
