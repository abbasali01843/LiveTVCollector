from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/Osares10/ipmx/refs/heads/main/Mexico.m3u",
    "https://raw.githubusercontent.com/Edgar-Reyna/ListaIPTV/refs/heads/main/FULLTV.M3U",
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_MX.m3u",
    "https://iptv-org.github.io/iptv/countries/mx.m3u",
]


def main():
    collector = Collector(country="Mexico", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
