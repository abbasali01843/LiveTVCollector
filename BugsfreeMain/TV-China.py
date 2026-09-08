from BugsfreeCore.collector import Collector


SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
    "https://raw.githubusercontent.com/TianmuTNT/iptv/refs/heads/main/iptv.m3u",
    "https://iptv.wwkejishe.top/tv.m3u",
    "https://iptv.wwkejishe.top/Sub.m3u",
    "https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv6.m3u",
    "https://raw.githubusercontent.com/YueChan/Live/refs/heads/main/Global.m3u",
    "https://raw.githubusercontent.com/sjnhnp/adblock/refs/heads/main/filtered_https_only.m3u",
]


def main():
    collector = Collector(country="China", check_links=False)
    collector.process_sources(SOURCES)
    collector.export()
    print(f"Collected {len(collector.channels)} unique channels for China")


if __name__ == "__main__":
    main()
