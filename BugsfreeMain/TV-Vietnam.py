from BugsfreeCore.collector import Collector

SOURCES = [
    "https://raw.githubusercontent.com/HaNoiIPTV/HaNoiIPTV.m3u/refs/heads/master/Danh%20s%C3%A1ch%20k%C3%AAnh/G%C3%B3i%20ch%C3%ADnh%20th%E1%BB%A9c/Qu%C3%AA%20h%C6%B0%C6%A1ng%20H%C3%A0%20N%E1%BB%99i%20IPTV.m3u",
    "https://iptv-org.github.io/iptv/countries/vn.m3u",
]


def main():
    collector = Collector(country="Vietnam", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()


if __name__ == "__main__":
    main()
