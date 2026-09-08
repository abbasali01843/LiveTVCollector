from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/JekaLich/smtk/refs/heads/main/tv.smtk.m3u",
    "https://raw.githubusercontent.com/blackbirdstudiorus/LoganetXIPTV/main/LoganetXAll.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/MaximKiselev/iptv/main/playlist.m3u",
    "https://iptv-org.github.io/iptv/countries/ru.m3u",
]


def main():
    collector = Collector(country="Russia", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
