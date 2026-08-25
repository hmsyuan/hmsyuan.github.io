"""Render PTT2 records as reviewable Hugo draft bundles."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(value: str, fallback: str = "item") -> str:
    value = SAFE_NAME_RE.sub("-", value.strip()).strip("-.").lower()
    return value[:80] or fallback


def toml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def parse_ptt_date(value: Any, fallback: datetime) -> datetime:
    text = str(value or "").strip()
    for pattern in (
        "%a %b %d %H:%M:%S %Y",
        "%a %b %d %H:%M:%S %z %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(text, pattern)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return fallback


def fenced_text(value: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{value.rstrip()}\n{fence}"


def _front_matter(fields: list[tuple[str, Any]]) -> str:
    lines = ["+++"]
    for key, value in fields:
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, int):
            rendered = str(value)
        elif isinstance(value, list):
            rendered = "[" + ", ".join(toml_string(item) for item in value) + "]"
        else:
            rendered = toml_string(value)
        lines.append(f"{key} = {rendered}")
    lines.append("+++")
    return "\n".join(lines)


def _base_fields(
    *, title: str, author: str, date: datetime, board: str, source_kind: str
) -> list[tuple[str, Any]]:
    return [
        ("author", author),
        ("title", title),
        ("date", date.isoformat()),
        ("draft", True),
        ("tags", ["PTT2", board]),
        ("categories", ["PTT2 匯入"]),
        ("summary", f"從 PTT2 {board} 匯入的{source_kind}草稿"),
        ("showtoc", False),
        ("tocopen", False),
        ("ShowReadingTime", False),
        ("ShowWordCount", False),
        ("disableShare", False),
        ("comments", True),
        ("ptt2_board", board),
        ("ptt2_source_kind", source_kind),
    ]


def _clean_comment(comment: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": comment.get("type"),
        "author": comment.get("author"),
        "content": comment.get("content"),
        "time": comment.get("time"),
    }


def write_regular_post(
    post: dict[str, Any],
    *,
    board: str,
    content_root: Path,
    raw_root: Path,
    exported_at: datetime,
) -> dict[str, Any]:
    index = int(post.get("index") or 0)
    aid = str(post.get("aid") or "")
    title = str(post.get("title") or f"PTT2 article {index}")
    author = str(post.get("author") or "PTT2")
    date = parse_ptt_date(post.get("date"), exported_at)
    identifier = safe_name(aid, str(index or "unknown"))
    stem = f"{date:%Y-%m-%d}-{index:06d}-{identifier}"

    fields = _base_fields(
        title=title,
        author=author,
        date=date,
        board=board,
        source_kind="一般文章",
    )
    fields.extend(
        [
            ("slug", f"ptt2-{safe_name(board)}-{identifier}"),
            ("ptt2_aid", aid),
            ("ptt2_index", index),
        ]
    )

    content = str(post.get("content") or "")
    comments = [
        _clean_comment(item)
        for item in (post.get("comments") or [])
        if isinstance(item, dict)
    ]
    body = [
        _front_matter(fields),
        "",
        "> 自動匯入的公開 PTT2 內容；預設為草稿，發布前請確認內容與授權。",
        "",
        fenced_text(content),
    ]
    if comments:
        body.extend(["", "## 回應", ""])
        for item in comments:
            label = " ".join(
                str(item.get(key) or "").strip()
                for key in ("type", "author", "time")
            ).strip()
            body.append(f"- **{label or '回應'}**：{item.get('content') or ''}")

    content_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    markdown_path = content_root / f"{stem}.md"
    raw_path = raw_root / f"{stem}.json"
    markdown_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")

    raw_record = {
        "board": board,
        "aid": aid,
        "index": index,
        "author": author,
        "title": title,
        "date": post.get("date"),
        "list_date": post.get("list_date"),
        "content": content,
        "comments": comments,
        "post_status": post.get("post_status"),
    }
    raw_path.write_text(
        json.dumps(raw_record, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": "post",
        "index": index,
        "aid": aid,
        "title": title,
        "hugo_path": markdown_path.as_posix(),
        "raw_path": raw_path.as_posix(),
        "sha256": hashlib.sha256(markdown_path.read_bytes()).hexdigest(),
    }


def write_essence_document(
    document: Any,
    *,
    board: str,
    sequence: int,
    content_root: Path,
    raw_root: Path,
    exported_at: datetime,
) -> dict[str, Any]:
    record = asdict(document) if is_dataclass(document) else dict(document)
    title = str(record.get("title") or f"精華區文件 {sequence}")
    text = str(record.get("content") or "")
    menu_path = [str(item) for item in (record.get("menu_path") or [])]
    path_key = "/".join(menu_path + [title])
    digest = hashlib.sha1(path_key.encode("utf-8")).hexdigest()[:12]
    stem = f"essence-{sequence:05d}-{digest}"

    fields = _base_fields(
        title=title,
        author="PTT2 精華區",
        date=exported_at,
        board=board,
        source_kind="精華區文件",
    )
    fields.extend(
        [
            ("slug", f"ptt2-{safe_name(board)}-{stem}"),
            ("ptt2_essence_path", " / ".join(menu_path + [title])),
        ]
    )
    body = [
        _front_matter(fields),
        "",
        "> 自動匯入的公開 PTT2 精華區內容；預設為草稿，發布前請確認內容與授權。",
        "",
        fenced_text(text),
    ]

    content_root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    markdown_path = content_root / f"{stem}.md"
    raw_path = raw_root / f"{stem}.json"
    markdown_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    raw_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": "essence",
        "title": title,
        "menu_path": menu_path,
        "hugo_path": markdown_path.as_posix(),
        "raw_path": raw_path.as_posix(),
        "sha256": hashlib.sha256(markdown_path.read_bytes()).hexdigest(),
    }
