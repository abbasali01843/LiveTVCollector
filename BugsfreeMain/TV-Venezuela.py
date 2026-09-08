from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/Nuelmaos/ipTV/refs/heads/Inicio/modo_prueba_xtraplus_102420.m3u",
    "https://raw.githubusercontent.com/Nuelmaos/ipTV/refs/heads/Inicio/modo_prueba_92430.m3u",
    "https://iptv-org.github.io/iptv/countries/ve.m3u",
]


def main():
    collector = Collector(country="Venezuela", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
