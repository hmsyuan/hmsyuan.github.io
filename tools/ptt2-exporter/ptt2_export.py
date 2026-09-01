#!/usr/bin/env python3
"""Export a public PTT2 board and its essence tree into a Hugo-ready ZIP."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import PyPtt

from essence import crawl_essence
from hugo_export import write_essence_document, write_regular_post
from ptt2_client import GuestCapacityError, login_with_retry


IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def sanitize_error(value: str) -> str:
    value = IPV4_RE.sub("[redacted-ip]", value)
    return EMAIL_RE.sub("[redacted-email]", value)


def make_paths_portable(record: dict[str, Any], bundle_root: Path) -> dict[str, Any]:
    for key in ("hugo_path", "raw_path"):
        record[key] = Path(record[key]).relative_to(bundle_root).as_posix()
    return record


def fetch_post_list(bot: PyPtt.API, board: str, max_posts: int) -> list[dict[str, Any]]:
    newest = bot.get_newest_index(PyPtt.NewIndex.BOARD, board=board)
    wanted = newest if max_posts == 0 else min(newest, max_posts)
    records: dict[int, dict[str, Any]] = {}
    offset = 0

    while offset < wanted:
        limit = min(100, wanted - offset)
        for item in bot.get_post_list(board=board, limit=limit, offset=offset):
            index = int(item.get("index") or 0)
            if index > 0:
                records[index] = item
        offset += limit

    return [records[index] for index in sorted(records)]


def export_posts(
    bot: PyPtt.API,
    board: str,
    max_posts: int,
    bundle_root: Path,
    exported_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries = fetch_post_list(bot, board, max_posts)
    exported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    content_root = bundle_root / "content" / "posts" / "ptt2" / board
    raw_root = bundle_root / "ptt2-archive" / board / "posts"

    for position, summary in enumerate(summaries, start=1):
        index = int(summary.get("index") or 0)
        print(f"[{position}/{len(summaries)}] post index {index}", flush=True)
        try:
            post = bot.get_post(board=board, index=index)
            if not post.get("content"):
                errors.append(
                    {"kind": "post", "index": index, "error": "no readable content"}
                )
                continue
            exported.append(
                make_paths_portable(
                    write_regular_post(
                        post,
                        board=board,
                        content_root=content_root,
                        raw_root=raw_root,
                        exported_at=exported_at,
                    ),
                    bundle_root,
                )
            )
        except Exception as exc:
            errors.append(
                {
                    "kind": "post",
                    "index": index,
                    "error": sanitize_error(f"{type(exc).__name__}: {exc}"),
                }
            )
        time.sleep(0.05)

    return exported, errors


def export_essence(
    bot: PyPtt.API,
    board: str,
    max_documents: int,
    bundle_root: Path,
    exported_at: datetime,
) -> list[dict[str, Any]]:
    documents = crawl_essence(
        bot,
        board,
        max_documents=max_documents,
    )
    content_root = bundle_root / "content" / "posts" / "ptt2" / board / "essence"
    raw_root = bundle_root / "ptt2-archive" / board / "essence"
    return [
        make_paths_portable(
            write_essence_document(
                document,
                board=board,
                sequence=sequence,
                content_root=content_root,
                raw_root=raw_root,
                exported_at=exported_at,
            ),
            bundle_root,
        )
        for sequence, document in enumerate(documents, start=1)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", default="InAddition")
    parser.add_argument("--scope", choices=("both", "posts", "essence"), default="both")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=0,
        help="Newest regular posts to export; 0 means all",
    )
    parser.add_argument(
        "--max-essence-documents",
        type=int,
        default=0,
        help="Essence documents to export; 0 means all",
    )
    parser.add_argument("--guest-attempts", type=int, default=4)
    parser.add_argument("--output", default="ptt2-export")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_posts < 0 or args.max_essence_documents < 0:
        raise SystemExit("max values must be zero or positive")

    board = args.board.strip()
    if not board or not all(char.isalnum() or char in "_-" for char in board):
        raise SystemExit("board must contain only letters, numbers, '_' or '-'")

    bundle_root = Path(args.output).resolve()
    bundle_root.mkdir(parents=True, exist_ok=True)
    exported_at = datetime.now(timezone.utc)
    ptt_id = os.environ.get("PTT2_ID") or "guest"
    password = os.environ.get("PTT2_PASSWORD") or ""
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "board": board,
        "scope": args.scope,
        "exported_at": exported_at.isoformat(),
        "login_mode": "guest" if ptt_id.lower() == "guest" else "credential",
        "draft": True,
        "items": [],
        "errors": [],
    }

    bot = None
    try:
        bot = login_with_retry(
            ptt_id,
            password,
            guest_attempts=args.guest_attempts,
        )
        if args.scope in ("both", "posts"):
            posts, errors = export_posts(
                bot,
                board,
                args.max_posts,
                bundle_root,
                exported_at,
            )
            manifest["items"].extend(posts)
            manifest["errors"].extend(errors)
        if args.scope in ("both", "essence"):
            manifest["items"].extend(
                export_essence(
                    bot,
                    board,
                    args.max_essence_documents,
                    bundle_root,
                    exported_at,
                )
            )
    except GuestCapacityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if bot is not None:
            try:
                bot.logout()
            except Exception:
                pass

    manifest["counts"] = {
        "posts": sum(item["kind"] == "post" for item in manifest["items"]),
        "essence": sum(item["kind"] == "essence" for item in manifest["items"]),
        "errors": len(manifest["errors"]),
    }
    (bundle_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    shutil.make_archive(str(bundle_root), "zip", root_dir=bundle_root)
    print(f"Exported bundle: {bundle_root}.zip")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
