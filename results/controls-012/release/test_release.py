"""Non-numerical allowlist and path-safety checks; no event body is opened."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_packet


class ReleasePlanTests(unittest.TestCase):
    def test_safe_relative_path_policy(self):
        good = "work/transition-extracted-final/repo/data/derived/012/events/row-000/native-primary.jsonl.gz"
        self.assertEqual(build_packet.safe_relative(good).as_posix(), good)
        for bad in ("/tmp/file", "../work/file", "work//file", "work/./file",
                    "private/anything", "work/vendor/module.py", "work/weights/model.bin",
                    "work/mailbox/receipt.json", "work/credentials/token"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                build_packet.safe_relative(bad)

    def test_rejects_source_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "work").mkdir()
            (root / "work" / "linked").symlink_to(root)
            with mock.patch.object(build_packet, "PROJECT", root):
                with self.assertRaises(ValueError):
                    build_packet.source_file("work/linked/file.txt")

    def test_exact_frozen_allowlist_categories(self):
        entries = build_packet.expected_sources()
        kinds = [item[0] for item in entries.values()]
        self.assertEqual(kinds.count("protocol_source"), 12)
        self.assertEqual(kinds.count("selected_event_partition"), 24)
        self.assertEqual(kinds.count("replication_metadata_input"), 26)
        self.assertEqual(kinds.count("explicit_support"), len(build_packet.EXTRA_PATHS))
        self.assertEqual(len(entries), 62 + len(build_packet.EXTRA_PATHS))
        for path in entries:
            build_packet.safe_relative(path)
        self.assertIn("work/transition-extracted-final/repo/results/012/analysis.sqlite", entries)
        self.assertIn("work/database-release/final/catalog.sqlite", entries)
        self.assertNotIn("work/next-study/intake-2026-09-28/vendor-check.json", entries)


if __name__ == "__main__":
    unittest.main()
