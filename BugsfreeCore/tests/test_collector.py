import os
import tempfile
import unittest

from BugsfreeCore.collector import Collector, normalize_url


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.collector = Collector(country="Test", base_dir="/tmp/live-tv-tests")

    def test_parse_m3u_with_attributes(self):
        text = '#EXTM3U\n#EXTINF:-1 tvg-id="news" tvg-logo="https://example.com/logo.png" group-title="News",Example News\nhttps://example.com/live/news.m3u8\n'
        self.collector.parse_m3u(text, "https://example.com/list.m3u")
        self.assertEqual(len(self.collector.channels), 1)
        item = self.collector.channels[0]
        self.assertEqual(item["name"], "Example News")
        self.assertEqual(item["group"], "News")
        self.assertEqual(item["logo"], "https://example.com/logo.png")
        self.assertEqual(item["url"], "https://example.com/live/news.m3u8")
        self.assertEqual(item["type"], "hls")

    def test_json_normalization(self):
        text = '[{"title":"Channel A","stream_url":"https://example.com/a.m3u8","group":"News"}]'
        self.assertTrue(self.collector.parse_json(text, "https://example.com/channels.json"))
        self.assertEqual(len(self.collector.channels), 1)
        item = self.collector.channels[0]
        self.assertEqual(item["name"], "Channel A")
        self.assertEqual(item["url"], "https://example.com/a.m3u8")
        self.assertEqual(item["group"], "News")

    def test_html_relative_urls(self):
        html = '<a href="streams/channel.m3u8">Channel</a>'
        self.collector.parse_html(html, "https://example.com/player/index.html")
        urls = {item["url"] for item in self.collector.channels}
        self.assertIn("https://example.com/player/streams/channel.m3u8", urls)

    def test_protocol_detection(self):
        self.assertEqual(self.collector.detect_type("https://example.com/a.m3u8"), "hls")
        self.assertEqual(self.collector.detect_type("https://example.com/a.mpd"), "dash")
        self.assertEqual(self.collector.detect_type("https://example.com/a.mp4"), "media")
        self.assertEqual(self.collector.detect_type("https://example.com/live/channel"), "unknown")

    def test_url_normalization(self):
        url = "https://EXAMPLE.com:443/live/a.m3u8?utm_source=test&token=abc"
        normalized = normalize_url(url)
        self.assertEqual(normalized, "https://example.com:443/live/a.m3u8?token=abc")

    def test_export_file_prefix_and_playlist_escaping(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = Collector(country="X", base_dir=tmp, file_prefix="Movies")
            collector.add('Na"me\nInjected', "https://example.com/v.m3u8",
                          'Gr"oup', "https://example.com/l.png", "src")
            collector.export()
            out = os.path.join(tmp, "X")
            for name in ("Movies.json", "Movies", "Movies.m3u", "Movies.txt"):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)
            m3u = open(os.path.join(out, "Movies.m3u"), encoding="utf-8").read()
            lines = m3u.splitlines()
            self.assertEqual(len(lines), 3)  # no injected extra lines
            self.assertIn('group-title="Gr&quot;oup"', lines[1])
            self.assertTrue(lines[1].endswith(',Na"me Injected'))


if __name__ == "__main__":
    unittest.main()
