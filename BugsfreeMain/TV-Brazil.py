from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/GelsondoForro/Listas-m3u/refs/heads/main/Lista.m3u",
    "https://raw.githubusercontent.com/Edgar-Reyna/ListaIPTV/refs/heads/main/FULLTV.M3U",
    "https://raw.githubusercontent.com/HelmerLuzo/PlutoTV_HL/refs/heads/main/tv/m3u/PlutoTV_tv_BR.m3u",
    "https://iptv-org.github.io/iptv/countries/br.m3u",
]


def main():
    collector = Collector(country="Brazil", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
