import unittest

from BugsfreeCore.collector import Collector


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.collector = Collector(country="Test", base_dir="/tmp/live-tv-tests")

    def test_parse_m3u_with_attributes(self):
        text = '''#EXTM3U\n#EXTINF:-1 tvg-id="news" tvg-logo="https://example.com/logo.png" group-title="News",Example News\nhttps://example.com/live/news.m3u8\n'''
        items = self.collector.parse_m3u(text, "https://example.com/list.m3u")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Example News")
        self.assertEqual(items[0]["group"], "News")
        self.assertEqual(items[0]["logo"], "https://example.com/logo.png")
        self.assertEqual(items[0]["url"], "https://example.com/live/news.m3u8")

    def test_json_normalization(self):
        text = '''[{"title":"Channel A","stream_url":"https://example.com/a.m3u8","group":"News"}]'''
        items = self.collector.parse_json(text, "https://example.com/channels.json")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Channel A")
        self.assertEqual(items[0]["url"], "https://example.com/a.m3u8")
        self.assertEqual(items[0]["group"], "News")

    def test_html_relative_urls(self):
        html = '<a href="streams/channel.m3u8">Channel</a>'
        items = self.collector.parse_html(html, "https://example.com/player/index.html")
        urls = {item["url"] for item in items}
        self.assertIn("https://example.com/player/streams/channel.m3u8", urls)

    def test_protocol_detection(self):
        self.assertEqual(self.collector.detect_protocol("https://example.com/a.m3u8"), "hls")
        self.assertEqual(self.collector.detect_protocol("https://example.com/a.mpd"), "dash")
        self.assertEqual(self.collector.detect_protocol("https://example.com/a.mp4"), "media")

    def test_url_normalization(self):
        url = "https://EXAMPLE.com:443/live/a.m3u8?utm_source=test&token=abc"
        normalized = self.collector.normalize_url(url)
        self.assertEqual(normalized, "https://example.com/live/a.m3u8?token=abc")


if __name__ == "__main__":
    unittest.main()
