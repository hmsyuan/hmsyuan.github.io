"""Recursive reader for PTT2's terminal-only z/essence tree."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from PyPtt import _api_util, command, connect_core, screens


MENU_ROW_RE = re.compile(
    r"^\s*(?:>|●)?\s*(\d+)[.)]\s*([◆◇◎●○□■★]?)\s*(.*?)\s*$"
)
MENU_WORDS = ("精華區", "精華文章", "目錄")


@dataclass(frozen=True)
class MenuEntry:
    index: int
    marker: str
    title: str


@dataclass(frozen=True)
class EssenceDocument:
    title: str
    menu_path: list[str]
    content: str


def parse_menu_entries(screen: str) -> list[MenuEntry]:
    """Extract selectable numbered rows from a rendered essence menu."""
    entries: dict[int, MenuEntry] = {}
    for line in screen.splitlines():
        match = MENU_ROW_RE.match(line)
        if not match:
            continue
        index = int(match.group(1))
        marker = match.group(2)
        title = match.group(3).strip()
        if not title or title.startswith(("瀏覽", "說明")):
            continue
        entries[index] = MenuEntry(index=index, marker=marker, title=title)
    return [entries[index] for index in sorted(entries)]


def merge_visible_lines(accumulated: list[str], visible: list[str]) -> list[str]:
    """Merge overlapping terminal pages without repeating retained rows."""
    if not accumulated:
        return visible.copy()
    max_overlap = min(len(accumulated), len(visible))
    for size in range(max_overlap, 0, -1):
        if accumulated[-size:] == visible[:size]:
            return accumulated + visible[size:]
    return accumulated + visible


def _menu_targets() -> list[connect_core.TargetUnit]:
    return [
        connect_core.TargetUnit(word, break_detect=True, refresh=False)
        for word in MENU_WORDS
    ]


def _last_screen(bot: Any) -> str:
    queue = bot.connect_core.get_screen_queue()
    return queue[-1] if queue else ""


def scan_current_menu(bot: Any, *, max_pages: int = 500) -> list[MenuEntry]:
    entries: dict[int, MenuEntry] = {}
    previous_ids: set[int] = set()

    for _ in range(max_pages):
        screen = _last_screen(bot)
        for entry in parse_menu_entries(screen):
            entries[entry.index] = entry
        current_ids = set(entries)

        if "(100%)" in screen or "（100%）" in screen:
            break
        if current_ids == previous_ids and previous_ids:
            break
        previous_ids = current_ids.copy()

        result = bot.connect_core.send(
            command.page_down,
            _menu_targets(),
            screen_timeout=3.0,
            refresh=False,
        )
        if result < 0:
            break

    return [entries[index] for index in sorted(entries)]


def _open_entry(bot: Any, index: int) -> str:
    targets = [
        connect_core.TargetUnit(
            screens.Target.InPost, break_detect=True, refresh=False
        ),
        *_menu_targets(),
        connect_core.TargetUnit("任意鍵", response=" ", refresh=False),
    ]
    result = bot.connect_core.send(
        str(index) + command.enter,
        targets,
        screen_timeout=5.0,
        refresh=False,
    )
    if result == 0:
        return "document"
    if 1 <= result <= len(MENU_WORDS):
        return "directory"
    raise RuntimeError(f"Could not classify essence item {index}; match={result}")


def _leave_current_item(bot: Any) -> None:
    bot.connect_core.send(
        command.left,
        _menu_targets(),
        screen_timeout=5.0,
        refresh=False,
    )


def capture_current_document(bot: Any, *, max_steps: int = 10000) -> str:
    accumulated: list[str] = []

    for _ in range(max_steps):
        screen = _last_screen(bot)
        lines = screen.splitlines()
        if lines and "瀏覽" in lines[-1] and "頁" in lines[-1]:
            lines = lines[:-1]
        while lines and not lines[-1].strip():
            lines.pop()
        accumulated = merge_visible_lines(accumulated, lines)

        if "(100%)" in screen or "（100%）" in screen:
            break
        result = bot.connect_core.send(
            command.down,
            [
                connect_core.TargetUnit(
                    screens.Target.PostEnd, break_detect=True, refresh=False
                ),
                connect_core.TargetUnit(
                    screens.Target.InPost, break_detect=True, refresh=False
                ),
            ],
            screen_timeout=5.0,
            refresh=False,
        )
        if result < 0:
            raise RuntimeError("Timed out while reading an essence document")
    else:
        raise RuntimeError("Essence document exceeded the terminal step limit")

    return "\n".join(accumulated).strip()


def crawl_essence(
    bot: Any,
    board: str,
    *,
    max_depth: int = 30,
    max_documents: int = 0,
) -> list[EssenceDocument]:
    """Walk the board's essence tree and return every readable document."""
    _api_util.goto_board(bot, board, refresh=True)
    targets = [
        *_menu_targets(),
        connect_core.TargetUnit("無精華區", break_detect=True, refresh=False),
        connect_core.TargetUnit("任意鍵", response=" ", refresh=False),
    ]
    result = bot.connect_core.send(
        "z",
        targets,
        screen_timeout=5.0,
        refresh=False,
    )
    if result == len(MENU_WORDS):
        return []
    if result < 0:
        raise RuntimeError("Could not enter the board's essence area")

    documents: list[EssenceDocument] = []

    def walk(menu_path: list[str], depth: int) -> None:
        if depth > max_depth:
            raise RuntimeError(f"Essence tree exceeded max depth {max_depth}")
        entries = scan_current_menu(bot)
        for entry in entries:
            if max_documents and len(documents) >= max_documents:
                return
            kind = _open_entry(bot, entry.index)
            if kind == "document":
                content = capture_current_document(bot)
                documents.append(
                    EssenceDocument(
                        title=entry.title,
                        menu_path=menu_path.copy(),
                        content=content,
                    )
                )
                _leave_current_item(bot)
            else:
                walk(menu_path + [entry.title], depth + 1)
                _leave_current_item(bot)

    walk([], 0)
    return documents
