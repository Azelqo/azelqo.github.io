#!/usr/bin/env python3
"""Sync published Notion database pages to Hugo Markdown posts.

Required environment:
  NOTION_TOKEN
  NOTION_DATA_SOURCE_ID
Optional:
  NOTION_API_VERSION (defaults to 2025-09-03)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.notion.com/v1"
TOKEN = os.environ["NOTION_TOKEN"]
DATA_SOURCE_ID = os.environ["NOTION_DATA_SOURCE_ID"]
VERSION = os.getenv("NOTION_API_VERSION", "2025-09-03")
OUT = Path("content/notion")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": VERSION,
    "Content-Type": "application/json",
}


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"Notion API {exc.code}: {detail}") from exc


def paginated(path: str, payload: dict | None = None):
    body = dict(payload or {})
    while True:
        result = request("POST", path, body)
        yield from result.get("results", [])
        if not result.get("has_more"):
            break
        body["start_cursor"] = result["next_cursor"]


def plain(rich_text: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text or [])


def prop_text(props: dict, name: str, kind: str = "rich_text") -> str:
    value = props.get(name, {})
    if kind == "title":
        return plain(value.get("title", []))
    return plain(value.get("rich_text", []))


def prop_select(props: dict, name: str) -> str:
    return (props.get(name, {}).get("select") or {}).get("name", "")


def prop_multi(props: dict, name: str) -> list[str]:
    return [x.get("name", "") for x in props.get(name, {}).get("multi_select", []) if x.get("name")]


def rich_to_md(items: list[dict]) -> str:
    out = []
    for item in items or []:
        value = item.get("plain_text", "")
        ann = item.get("annotations", {})
        if ann.get("code"):
            value = f"`{value}`"
        if ann.get("bold"):
            value = f"**{value}**"
        if ann.get("italic"):
            value = f"*{value}*"
        if ann.get("strikethrough"):
            value = f"~~{value}~~"
        if ann.get("underline"):
            value = f"<u>{value}</u>"
        href = (item.get("href") or (item.get("text") or {}).get("link", {}) or {}).get("url")
        if href:
            value = f"[{value}]({href})"
        out.append(value)
    return "".join(out)


def block_text(block: dict) -> str:
    kind = block.get("type", "")
    data = block.get(kind, {})
    if kind in ("paragraph", "heading_1", "heading_2", "heading_3", "quote", "callout"):
        value = rich_to_md(data.get("rich_text", []))
        if kind == "heading_1":
            return "# " + value
        if kind == "heading_2":
            return "## " + value
        if kind == "heading_3":
            return "### " + value
        if kind == "quote":
            return "> " + value
        if kind == "callout":
            return "> " + value
        return value
    if kind == "bulleted_list_item":
        return "- " + rich_to_md(data.get("rich_text", []))
    if kind == "numbered_list_item":
        return "1. " + rich_to_md(data.get("rich_text", []))
    if kind == "to_do":
        mark = "x" if data.get("checked") else " "
        return f"- [{mark}] " + rich_to_md(data.get("rich_text", []))
    if kind == "code":
        lang = data.get("language", "")
        return f"```{lang}\n{rich_to_md(data.get('rich_text', []))}\n```"
    if kind == "divider":
        return "---"
    if kind == "bookmark":
        url = data.get("url", "")
        caption = rich_to_md(data.get("caption", [])) or url
        return f"[{caption}]({url})"
    if kind == "image":
        item = data.get("file") or data.get("external") or {}
        url = item.get("url", "")
        caption = rich_to_md(data.get("caption", []))
        return f"![{caption}]({url})" if url else caption
    if kind == "embed":
        url = data.get("url", "")
        return f"[{url}]({url})"
    return ""


def get_page_markdown(page_id: str) -> str:
    chunks = []
    for block in paginated(f"/blocks/{page_id}/children", {"page_size": 100}):
        value = block_text(block)
        if value:
            chunks.append(value)
        if block.get("has_children"):
            nested = []
            for child in paginated(f"/blocks/{block['id']}/children", {"page_size": 100}):
                rendered = block_text(child)
                if rendered:
                    nested.append("  " + rendered.replace("\n", "\n  "))
            if nested:
                chunks.extend(nested)
    return "\n\n".join(chunks).strip()


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9ぁ-んァ-ン一-龥ー]+", "-", value)
    return value.strip("-") or "note"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = list(paginated(f"/data_sources/{DATA_SOURCE_ID}/query", {"page_size": 100}))
    keep: set[str] = set()
    published = 0

    for page in pages:
        props = page.get("properties", {})
        if prop_select(props, "Status") != "公開":
            continue
        title = prop_text(props, "Title", "title").strip()
        if not title:
            print(f"Skip page {page['id']}: Title is empty")
            continue

        slug = prop_text(props, "Slug").strip() or slugify(title)
        slug = re.sub(r"[^a-zA-Z0-9ぁ-んァ-ン一-龥_-]+", "-", slug).strip("-")
        filename = f"{slug}.md"
        keep.add(filename)

        date_value = (props.get("Date", {}).get("date") or {}).get("start")
        if not date_value:
            date_value = page.get("created_time", dt.datetime.now(dt.timezone.utc).isoformat())
        if len(date_value) == 10:
            date_value += "T09:00:00+09:00"
        description = prop_text(props, "Description").strip()
        tags = prop_multi(props, "Tags")
        categories = prop_multi(props, "Categories")
        body = get_page_markdown(page["id"])
        front = [
            "---",
            f"title: {yaml_string(title)}",
            f"description: {yaml_string(description)}",
            f"date: {yaml_string(date_value)}",
            f"lastmod: {yaml_string(dt.datetime.now(dt.timezone.utc).isoformat())}",
            'author: "Azelqo"',
            "draft: false",
            "categories:",
        ]
        front.extend([f"  - {yaml_string(x)}" for x in categories] or ["  - \"メモ\""])
        front.append("tags:")
        front.extend([f"  - {yaml_string(x)}" for x in tags])
        content = "\n".join(front) + "\n---\n\n" + body + "\n"
        (OUT / filename).write_text(content, encoding="utf-8")
        published += 1

    # Only remove Markdown files in this integration's dedicated directory.
    for existing in OUT.glob("*.md"):
        if existing.name not in keep:
            existing.unlink()
    print(f"Synced {published} published Notion page(s) into {OUT}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Notion sync failed: {exc}", file=sys.stderr)
        sys.exit(1)
