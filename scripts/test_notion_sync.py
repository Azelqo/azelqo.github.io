import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("NOTION_TOKEN", "unit-test-token")
os.environ.setdefault("NOTION_DATA_SOURCE_ID", "00000000-0000-0000-0000-000000000000")

from notion_sync import ensure_safe_publish_set


class NotionSyncSafetyTests(unittest.TestCase):
    def test_zero_published_pages_refuses_to_remove_existing_posts(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "previous-post.md"
            existing.write_text("keep me", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "refusing to delete existing posts"):
                ensure_safe_publish_set(0, [existing])
            self.assertTrue(existing.exists())

    def test_zero_published_pages_is_safe_when_there_are_no_existing_posts(self):
        ensure_safe_publish_set(0, [])

    def test_nonzero_published_pages_allows_normal_pruning(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "previous-post.md"
            existing.write_text("keep me", encoding="utf-8")
            ensure_safe_publish_set(2, [existing])


if __name__ == "__main__":
    unittest.main()
