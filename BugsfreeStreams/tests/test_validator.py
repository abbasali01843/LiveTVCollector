import json
import tempfile
import unittest
from pathlib import Path

from BugsfreeStreams import validator


class ValidatorTests(unittest.TestCase):
    def test_normalize_url_and_protocol(self):
        url = "https://EXAMPLE.com/live/a.m3u8?utm_source=test&token=abc"
        self.assertEqual(
            validator.normalize_url(url),
            "https://example.com/live/a.m3u8?token=abc",
        )
        self.assertEqual(validator.protocol(url), "hls")
        self.assertEqual(
            validator.protocol("https://example.com/manifest", "application/dash+xml"),
            "dash",
        )
        self.assertEqual(validator.protocol("https://example.com/video.mp4"), "media")

    def test_score_classes(self):
        self.assertEqual(validator.score("active", "hls"), 100)
        self.assertEqual(validator.score("active", "hls", redirected=True), 95)
        self.assertEqual(validator.score("geo_or_restricted", "hls"), 25)
        self.assertEqual(validator.score("timeout", "unknown"), 10)
        self.assertEqual(validator.score("down", "hls"), 0)

    def test_app_exports_include_only_active_streams(self):
        results = [
            {
                "name": "Active News",
                "url": "https://example.com/news.m3u8",
                "final_url": "https://cdn.example.com/news.m3u8",
                "logo": "https://example.com/news.png",
                "group": "News",
                "country": "Bangladesh",
                "source": "test",
                "status": "active",
                "protocol": "hls",
                "score": 100,
            },
            {
                "name": "Down Channel",
                "url": "https://example.com/down.m3u8",
                "final_url": "https://example.com/down.m3u8",
                "logo": "",
                "group": "News",
                "country": "Bangladesh",
                "source": "test",
                "status": "down",
                "protocol": "hls",
                "score": 0,
            },
            {
                "name": "Geo Channel",
                "url": "https://example.com/geo.m3u8",
                "final_url": "https://example.com/geo.m3u8",
                "logo": "",
                "group": "Sports",
                "country": "India",
                "source": "test",
                "status": "geo_or_restricted",
                "protocol": "hls",
                "score": 25,
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            old_out = validator.OUT
            validator.OUT = Path(tmp)
            try:
                validator.write_app_exports(results, "2026-09-08T00:00:00Z")
                active = json.loads((Path(tmp) / "active.json").read_text(encoding="utf-8"))
                countries = json.loads((Path(tmp) / "countries.json").read_text(encoding="utf-8"))
                playlist = (Path(tmp) / "active.m3u").read_text(encoding="utf-8")
            finally:
                validator.OUT = old_out

        self.assertEqual(active["count"], 1)
        self.assertEqual(active["channels"][0]["name"], "Active News")
        self.assertIn("https://cdn.example.com/news.m3u8", playlist)
        self.assertNotIn("down.m3u8", playlist)
        self.assertNotIn("geo.m3u8", playlist)
        self.assertEqual(countries["countries"]["Bangladesh"]["active"], 1)
        self.assertEqual(countries["countries"]["Bangladesh"]["down"], 1)
        self.assertEqual(countries["countries"]["India"]["geo_or_restricted"], 1)


if __name__ == "__main__":
    unittest.main()
