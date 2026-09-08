import logging
import sys

sys.path.insert(0, ".")
from BugsfreeCore.collector import Collector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SOURCES = [
    "https://raw.githubusercontent.com/abusaeeidx/Mrgify-BDIX-IPTV/main/playlist.m3u",
    "https://raw.githubusercontent.com/time2shine/Rokon-IPTV/main/playlist.m3u",
    "https://raw.githubusercontent.com/abusaeeidx/Mrgify-Tv/main/playlist.m3u",
    "https://raw.githubusercontent.com/mhmimxl/filoox-bdix-selected/main/playlist.m3u",
    "https://raw.githubusercontent.com/sm-monirulislam/RoarZone-Auto-Update-playlist/main/RoarZone.m3u",
    "https://raw.githubusercontent.com/AHIL44444/GAZI-LIVE-TV-M3U8/refs/heads/main/index.html",
    "https://raw.githubusercontent.com/mr-masudrana/Web_Player-IPTV/refs/heads/main/channels.json",
    "https://iptv-org.github.io/iptv/countries/bd.m3u",
]


def main():
    # Collection remains fast; the unified validator is run separately so a
    # temporary source outage cannot erase the whole country's dataset.
    collector = Collector(country="Bangladesh", check_links=False, max_workers=20, timeout=8)
    collector.process_sources(SOURCES)
    collector.export()
    logging.info("Collected %d unique Bangladesh streams", len(collector.channels))


if __name__ == "__main__":
    main()
