#!/usr/bin/env python3
"""Read-only connectivity and screen probe for a public PTT2 board."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

import PyPtt
from PyPtt import _api_util, command, connect_core, data_type, exceptions, screens


IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def sanitize(value: str) -> str:
    """Keep structural diagnostics while removing incidental personal data."""
    value = IPV4_RE.sub("[redacted-ip]", value)
    return EMAIL_RE.sub("[redacted-email]", value)


def login_guest(bot: PyPtt.API) -> None:
    """Log in to PTT2's read-only guest session.

    PyPtt always submits ``account,password`` because registered accounts use
    that protocol.  PTT2's built-in guest account is different: it enters the
    main menu immediately after ``guest`` and never asks for a password.
    """
    bot.connect_core.connect()
    bot.ptt_id = "guest"
    bot._ptt_pw = ""

    targets = [
        connect_core.TargetUnit(screens.Target.MainMenu, break_detect=True),
        connect_core.TargetUnit("【看板列表】", response=command.go_main_menu),
        connect_core.TargetUnit("登入太頻繁", response=" "),
        connect_core.TargetUnit("系統過載", break_detect=True),
        connect_core.TargetUnit("任意鍵", response=" "),
        connect_core.TargetUnit("【分類看板】", response=command.go_main_menu),
        connect_core.TargetUnit("熱門話題", response=command.go_main_menu),
    ]
    bot.connect_core.send(
        "guest" + command.enter,
        targets,
        screen_timeout=bot.config.screen_long_timeout,
        refresh=False,
        secret=True,
    )

    queue = bot.connect_core.get_screen_queue()
    screen = queue[-1] if queue else ""
    if not all(target in screen for target in screens.Target.MainMenu):
        raise RuntimeError(
            "guest login did not reach the main menu; final screen:\n"
            + sanitize(screen)
        )

    if "> (" in screen:
        bot.cursor = data_type.Cursor.NEW
    elif "●(" in screen:
        bot.cursor = data_type.Cursor.OLD
    else:
        raise exceptions.UnknownError()

    screens.Target.InBoardWithCursor = screens.Target.InBoardWithCursor[
        : screens.Target.InBoardWithCursorLen
    ]
    screens.Target.InBoardWithCursor.append(bot.cursor)
    screens.Target.InMailBoxWithCursor = screens.Target.InMailBoxWithCursor[
        : screens.Target.InMailBoxWithCursorLen
    ]
    screens.Target.InMailBoxWithCursor.append(bot.cursor)

    bot.is_registered_user = False
    bot._is_login = True


def capture_essence_root(bot: PyPtt.API, board: str) -> dict[str, Any]:
    """Enter the board's z-menu and capture the rendered root screen.

    PyPtt does not currently expose a public API for the man/essence tree, so
    this probe deliberately uses its terminal core. The captured screen is
    used to build and verify a board-compatible state machine in the exporter.
    """
    _api_util.goto_board(bot, board, refresh=True)

    targets = [
        connect_core.TargetUnit("精華區", break_detect=True, refresh=False),
        connect_core.TargetUnit("目錄", break_detect=True, refresh=False),
        connect_core.TargetUnit("主題", break_detect=True, refresh=False),
        connect_core.TargetUnit("無精華區", break_detect=True, refresh=False),
        connect_core.TargetUnit("任意鍵", response=" ", refresh=False),
    ]

    result = bot.connect_core.send(
        "z",
        targets,
        screen_timeout=5.0,
        refresh=False,
    )

    queue = bot.connect_core.get_screen_queue()
    screen = queue[-1] if queue else ""
    return {
        "match_index": result,
        "screen": sanitize(screen),
    }


def probe(board: str) -> dict[str, Any]:
    ptt_id = os.environ.get("PTT2_ID") or "guest"
    ptt_password = os.environ.get("PTT2_PASSWORD") or ""

    bot = PyPtt.API(
        host=PyPtt.HOST.PTT2,
        log_level=PyPtt.LogLevel.INFO,
        screen_timeout=5.0,
        screen_long_timeout=15.0,
        screen_height=100,
    )

    report: dict[str, Any] = {
        "board": board,
        "login_mode": "credential" if ptt_id.lower() != "guest" else "guest",
        "host": "PTT2",
    }

    try:
        if ptt_id.lower() == "guest":
            login_guest(bot)
        else:
            bot.login(ptt_id=ptt_id, ptt_pw=ptt_password, kick_other_session=False)
        report["login"] = "ok"

        newest = bot.get_newest_index(PyPtt.NewIndex.BOARD, board=board)
        report["newest_index"] = newest

        if newest > 0:
            sample_size = min(3, newest)
            report["latest_posts"] = bot.get_post_list(
                board=board,
                limit=sample_size,
                offset=0,
            )
        else:
            report["latest_posts"] = []

        report["essence_root"] = capture_essence_root(bot, board)
        report["status"] = "ok"
        return report
    except Exception as exc:  # diagnostics must include the concrete failure
        report["status"] = "error"
        report["error_type"] = type(exc).__name__
        report["error"] = sanitize(str(exc))
        return report
    finally:
        try:
            bot.logout()
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", default="InAddition")
    parser.add_argument("--output", default="ptt2-probe.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = probe(args.board)
    payload = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    with open(args.output, "w", encoding="utf-8") as output_file:
        output_file.write(payload + "\n")
    print(payload)
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
