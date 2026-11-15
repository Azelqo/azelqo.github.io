#!/usr/bin/env python3
"""Sync published Notion database pages and site settings to Hugo."""
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
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": VERSION, "Content-Type": "application/json"}

def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Notion API {exc.code}: {exc.read().decode(errors='replace')}") from exc

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
    return plain(value.get("title" if kind == "title" else "rich_text", []))

def prop_select(props: dict, name: str) -> str:
    return (props.get(name, {}).get("select") or {}).get("name", "")

def prop_multi(props: dict, name: str) -> list[str]:
    return [x.get("name", "") for x in props.get(name, {}).get("multi_select", []) if x.get("name")]

def prop_checkbox(props: dict, name: str) -> bool:
    return bool(props.get(name, {}).get("checkbox", False))

def prop_number(props: dict, name: str, default: int) -> int:
    value = props.get(name, {}).get("number")
    return int(value) if value is not None else default

def rich_to_md(items: list[dict]) -> str:
    out = []
    for item in items or []:
        value = item.get("plain_text", "")
        ann = item.get("annotations", {})
        if ann.get("code"):
            value = chr(96) + value + chr(96)
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
        if kind == "heading_1": return "# " + value
        if kind == "heading_2": return "## " + value
        if kind == "heading_3": return "### " + value
        if kind in ("quote", "callout"): return "> " + value
        return value
    if kind == "bulleted_list_item": return "- " + rich_to_md(data.get("rich_text", []))
    if kind == "numbered_list_item": return "1. " + rich_to_md(data.get("rich_text", []))
    if kind == "to_do":
        return f"- [{'x' if data.get('checked') else ' '}] " + rich_to_md(data.get("rich_text", []))
    if kind == "code":
        fence = chr(96) * 3
        return fence + data.get("language", "") + "\n" + rich_to_md(data.get("rich_text", [])) + "\n" + fence
    if kind == "divider": return "---"
    if kind == "bookmark":
        url = data.get("url", "")
        return f"[{rich_to_md(data.get('caption', [])) or url}]({url})"
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
        if value: chunks.append(value)
        if block.get("has_children"):
            nested = []
            for child in paginated(f"/blocks/{block['id']}/children", {"page_size": 100}):
                rendered = block_text(child)
                if rendered: nested.append("  " + rendered.replace("\n", "\n  "))
            chunks.extend(nested)
    return "\n\n".join(chunks).strip()

def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9ぁ-んァ-ン一-龥ー]+", "-", value)
    return value.strip("-") or "note"

def apply_site_settings(props: dict) -> None:
    path = Path("hugo.toml")
    config = path.read_text(encoding="utf-8")
    def replace_one(pattern: str, replacement: str) -> None:
        nonlocal config
        config, count = re.subn(pattern, lambda _: replacement, config, count=1, flags=re.MULTILINE)
        if count != 1: raise RuntimeError(f"Could not update Hugo setting: {pattern}")
    def ts(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    replace_one(r"^title\s*=.*$", f"title = {ts(prop_text(props, 'SiteTitle') or 'Azelqoの備忘録')}")
    desc = ts(prop_text(props, "SiteDescription"))
    if re.search(r"^description\s*=.*$", config, flags=re.MULTILINE):
        replace_one(r"^description\s*=.*$", f"description = {desc}")
    else:
        config = re.sub(r"^(title\s*=.*)$", lambda m: m.group(1) + "\ndescription = " + desc, config, count=1, flags=re.MULTILINE)
    replace_one(r"^  emoji\s*=.*$", f"  emoji = {ts(prop_text(props, 'SidebarEmoji') or '🖥️')}")
    replace_one(r"^  subtitle\s*=.*$", f"  subtitle = {ts(prop_text(props, 'SidebarSubtitle'))}")
    replace_one(r"^  since\s*=.*$", f"  since = {prop_number(props, 'FooterSince', 2026)}")
    replace_one(r"^  default\s*=.*$", f"  default = {ts(prop_select(props, 'DefaultColorScheme') or 'auto')}")
    replace_one(r"^  toc\s*=.*$", f"  toc = {str(prop_checkbox(props, 'ShowTOC')).lower()}")
    replace_one(r"^  readingTime\s*=.*$", f"  readingTime = {str(prop_checkbox(props, 'ShowReadingTime')).lower()}")
    replace_one(r"(?<=\[params\.comments\]\n)  enabled\s*=.*$", f"  enabled = {str(prop_checkbox(props, 'ShowComments')).lower()}")
    path.write_text(config, encoding="utf-8")
    print("Applied Notion site settings to hugo.toml.")

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = list(paginated(f"/data_sources/{DATA_SOURCE_ID}/query", {"page_size": 100}))
    keep: set[str] = set()
    published = 0
    settings = None
    for page in pages:
        props = page.get("properties", {})
        status = prop_select(props, "Status")
        if status == "設定":
            settings = props
            continue
        if status != "公開": continue
        title = prop_text(props, "Title", "title").strip()
        if not title:
            print(f"Skip page {page['id']}: Title is empty")
            continue
        slug = prop_text(props, "Slug").strip() or slugify(title)
        slug = re.sub(r"[^a-zA-Z0-9ぁ-んァ-ン一-龥_-]+", "-", slug).strip("-")
        filename = f"{slug}.md"
        keep.add(filename)
        date_value = (props.get("Date", {}).get("date") or {}).get("start")
        if not date_value: date_value = page.get("created_time", dt.datetime.now(dt.timezone.utc).isoformat())
        if len(date_value) == 10: date_value += "T09:00:00+09:00"
        description = prop_text(props, "Description").strip()
        tags = prop_multi(props, "Tags")
        categories = prop_multi(props, "Categories")
        body = get_page_markdown(page["id"])
        front = [
            "---", f"title: {yaml_string(title)}", f"description: {yaml_string(description)}",
            f"date: {yaml_string(date_value)}", f"lastmod: {yaml_string(dt.datetime.now(dt.timezone.utc).isoformat())}",
            'author: "Azelqo"', "draft: false", "categories:",
        ]
        front.extend([f"  - {yaml_string(x)}" for x in categories] or ['  - "メモ"'])
        front.append("tags:")
        front.extend([f"  - {yaml_string(x)}" for x in tags])
        (OUT / filename).write_text("\n".join(front) + "\n---\n\n" + body + "\n", encoding="utf-8")
        published += 1

    if settings is not None:
        apply_site_settings(settings)
    else:
        print("No Notion site settings row found; Hugo settings left unchanged.")
    for existing in OUT.glob("*.md"):
        if existing.name not in keep: existing.unlink()
    print(f"Synced {published} published Notion page(s) into {OUT}.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Notion sync failed: {exc}", file=sys.stderr)
        sys.exit(1)
