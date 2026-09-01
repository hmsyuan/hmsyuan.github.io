from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from hugo_export import fenced_text, write_regular_post  # noqa: E402


class HugoExportTests(unittest.TestCase):
    def test_fence_expands_past_content_backticks(self) -> None:
        rendered = fenced_text("hello ``` embedded")
        self.assertTrue(rendered.startswith("````text\n"))
        self.assertTrue(rendered.endswith("\n````"))

    def test_regular_post_is_draft_and_drops_ip_fields(self) -> None:
        post = {
            "index": 42,
            "aid": "1Ab_CdEf",
            "author": "writer (Writer)",
            "title": "測試文章",
            "date": "Wed Aug 26 12:34:56 2026",
            "content": "正文",
            "ip": "192.0.2.1",
            "comments": [
                {
                    "type": "推",
                    "author": "reader",
                    "content": "收到",
                    "time": "08/26 13:00",
                    "ip": "198.51.100.2",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = write_regular_post(
                post,
                board="InAddition",
                content_root=root / "content",
                raw_root=root / "raw",
                exported_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            )
            markdown = Path(result["hugo_path"]).read_text(encoding="utf-8")
            raw = Path(result["raw_path"]).read_text(encoding="utf-8")
            self.assertIn("draft = true", markdown)
            self.assertIn('ptt2_board = "InAddition"', markdown)
            self.assertIn("測試文章", markdown)
            self.assertNotIn("192.0.2.1", markdown + raw)
            self.assertNotIn("198.51.100.2", markdown + raw)


if __name__ == "__main__":
    unittest.main()
