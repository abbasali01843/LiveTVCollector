import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from BugsfreeStreams import validator


class FakeResponse:
    def __init__(self, status_code=200, url="https://example.com/video.mp4", content_type="video/mp4", chunks=None, lines=None):
        self.status_code = status_code
        self.url = url
        self.headers = {"content-type": content_type}
        self._chunks = list(chunks or [b"video-data"])
        self._lines = list(lines or [])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_content(self, chunk_size=2048):
        yield from self._chunks

    def iter_lines(self):
        yield from self._lines


class FakeSession:
    def __init__(self, head_response=None, get_response=None):
        self.head_response = head_response
        self.get_response = get_response
        self.head_calls = 0
        self.get_calls = 0

    def head(self, *args, **kwargs):
        self.head_calls += 1
        if isinstance(self.head_response, Exception):
            raise self.head_response
        return self.head_response

    def get(self, *args, **kwargs):
        self.get_calls += 1
        if isinstance(self.get_response, Exception):
            raise self.get_response
        return self.get_response


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

    def test_head_timeout_falls_back_to_get(self):
        fake = FakeSession(
            head_response=requests.Timeout(),
            get_response=FakeResponse(),
        )
        with patch.object(validator, "session", return_value=fake):
            result = validator.probe({"name": "Video", "url": "https://example.com/video.mp4"})
        self.assertEqual(result["status"], "active")
        self.assertEqual(fake.head_calls, 1)
        self.assertEqual(fake.get_calls, 1)

    def test_hls_manifest_and_nested_playlist_are_probed(self):
        outer = FakeResponse(
            url="https://example.com/master.m3u8",
            content_type="application/vnd.apple.mpegurl",
            lines=[b"#EXTM3U", b"#EXT-X-STREAM-INF:BANDWIDTH=100000", b"child.m3u8"],
        )
        child = FakeResponse(
            url="https://example.com/child.m3u8",
            content_type="application/vnd.apple.mpegurl",
            lines=[b"#EXTM3U", b"#EXTINF:6,", b"segment.ts"],
        )
        segment = FakeResponse(
            url="https://example.com/segment.ts",
            content_type="video/mp2t",
            chunks=[b"segment-bytes"],
        )

        class HlsSession(FakeSession):
            def get(self, url, *args, **kwargs):
                self.get_calls += 1
                if url.endswith("master.m3u8"):
                    return outer
                if url.endswith("child.m3u8"):
                    return child
                return segment

        fake = HlsSession()
        with patch.object(validator, "session", return_value=fake):
            result = validator.probe({"name": "HLS", "url": "https://example.com/master.m3u8"})
        self.assertEqual(result["status"], "active")
        self.assertTrue(result["manifest_ok"])
        self.assertTrue(result["segment_ok"])
        self.assertEqual(fake.get_calls, 3)

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
