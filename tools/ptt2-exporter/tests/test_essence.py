from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

# Parser tests do not need a network client. Supply the minimal import surface
# so they can run even before PyPtt is installed in a local development shell.
if "PyPtt" not in sys.modules:
    pyptt = types.ModuleType("PyPtt")
    pyptt._api_util = object()
    pyptt.command = types.SimpleNamespace()
    pyptt.connect_core = types.SimpleNamespace(TargetUnit=object)
    pyptt.screens = types.SimpleNamespace()
    sys.modules["PyPtt"] = pyptt

from essence import merge_visible_lines, parse_menu_entries  # noqa: E402


class EssenceParserTests(unittest.TestCase):
    def test_parses_numbered_menu_rows(self) -> None:
        screen = """
【InAddition 精華區】
>   1. ◆ 公告與說明
    2. ◇ 第一篇文章
   18. ◎ 舊目錄
(q)離開
"""
        entries = parse_menu_entries(screen)
        self.assertEqual([entry.index for entry in entries], [1, 2, 18])
        self.assertEqual(entries[1].title, "第一篇文章")

    def test_merges_scrolled_terminal_windows(self) -> None:
        first = ["a", "b", "c"]
        second = ["b", "c", "d"]
        self.assertEqual(merge_visible_lines(first, second), ["a", "b", "c", "d"])


if __name__ == "__main__":
    unittest.main()
