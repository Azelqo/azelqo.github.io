#!/usr/bin/env python3
"""Sync published Notion database pages and site settings to Hugo."""
from __future__ import annotations
import datetime as dt
import hashlib
import io
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.request
import urllib.parse
from zoneinfo import ZoneInfo
from pathlib import Path
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

API = "https://api.notion.com/v1"
TOKEN = os.environ["NOTION_TOKEN"]
DATA_SOURCE_ID = os.environ["NOTION_DATA_SOURCE_ID"]
VERSION = os.getenv("NOTION_API_VERSION", "2025-09-03")
OUT = Path("content/posts/notion")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": VERSION, "Content-Type": "application/json"}

def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Notion API {exc.code} at {method} {path}: {exc.read().decode(errors='replace')}") from exc

def paginated(path: str, payload: dict | None = None):
    body = dict(payload or {})
    while True:
        result = request("POST", path, body)
        yield from result.get("results", [])
        if not result.get("has_more"):
            break
        body["start_cursor"] = result["next_cursor"]

def paginated_get(path: str):
    params = {"page_size": 100}
    while True:
        query = urllib.parse.urlencode(params)
        result = request("GET", f"{path}?{query}")
        yield from result.get("results", [])
        if not result.get("has_more"):
            break
        params["start_cursor"] = result["next_cursor"]

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
    for block in paginated_get(f"/blocks/{page_id}/children"):
        value = block_text(block)
        if value: chunks.append(value)
        if block.get("has_children"):
            nested = []
            for child in paginated_get(f"/blocks/{block['id']}/children"):
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

def sync_sidebar_avatar(props: dict) -> str | None:
    """Download, validate and normalize the Notion sidebar image.

    HEIC/HEIF uploads (common on iPhones) are converted to JPEG. A content hash
    in the filename prevents stale browser/CDN caches from showing the old icon.
    Existing files are removed only after a replacement has been fully validated.
    """
    files = (props.get("サイドバー画像", {}).get("files") or [])
    image_dir = Path("assets/img")
    image_dir.mkdir(parents=True, exist_ok=True)

    if not files:
        for old in image_dir.glob("notion-avatar*"):
            if old.is_file():
                old.unlink()
        return None

    item = files[0]
    source = item.get("file") or item.get("external") or {}
    url = source.get("url")
    if not url:
        raise RuntimeError("サイドバー画像 is set but has no downloadable URL")

    request_obj = urllib.request.Request(url, headers={"User-Agent": "Azelqo-Notion-Sync/1.0"})
    with urllib.request.urlopen(request_obj, timeout=30) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        content_type = response.headers.get_content_type().lower()

    if not data or len(data) > 8 * 1024 * 1024:
        raise RuntimeError("Sidebar avatar must be non-empty and 8 MB or smaller")

    # Detect the real file format from its bytes, not only the HTTP Content-Type.
    heif_brands = (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs")
    is_heif = len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in heif_brands
    signatures = [
        (".jpg", data.startswith(bytes.fromhex("ffd8ff"))),
        (".png", data.startswith(bytes.fromhex("89504e470d0a1a0a"))),
        (".webp", len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
        (".gif", data.startswith((b"GIF87a", b"GIF89a"))),
    ]
    detected = next((ext for ext, valid in signatures if valid), None)

    if is_heif:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                normalized = io.BytesIO()
                image.convert("RGB").save(normalized, format="JPEG", quality=92, optimize=True)
                data = normalized.getvalue()
                extension = ".jpg"
        except Exception as exc:
            raise RuntimeError(f"Could not decode/convert the HEIC/HEIF sidebar image: {exc}") from exc
    elif detected:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception as exc:
            raise RuntimeError(f"Sidebar image is damaged or invalid: {exc}") from exc
        extension = detected
    else:
        raise RuntimeError(
            "Unsupported sidebar image. Use JPEG, PNG, WebP, GIF, or HEIC/HEIF "
            f"(received Content-Type: {content_type or 'unknown'})."
        )

    digest = hashlib.sha256(data).hexdigest()[:12]
    target = image_dir / f"notion-avatar-{digest}{extension}"
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(target)

    # Keep the current image until the new one is safely written.
    for old in image_dir.glob("notion-avatar*"):
        if old.is_file() and old != target and not old.name.endswith(".tmp"):
            old.unlink()
    return f"img/{target.name}"


def apply_site_settings(props: dict) -> None:
    avatar_src = sync_sidebar_avatar(props)
    path = Path("hugo.toml")
    config = path.read_text(encoding="utf-8")
    def replace_one(pattern: str, replacement: str) -> None:
        nonlocal config
        config, count = re.subn(pattern, replacement if callable(replacement) else lambda _: replacement, config, count=1, flags=re.MULTILINE)
        if count != 1: raise RuntimeError(f"Could not update Hugo setting: {pattern}")
    def ts(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    replace_one(r"^title\s*=.*$", f"title = {ts(prop_text(props, 'サイト名') or 'Azelqoの備忘録')}")
    desc = ts(prop_text(props, "サイト説明"))
    if re.search(r"^description\s*=.*$", config, flags=re.MULTILINE):
        replace_one(r"^description\s*=.*$", f"description = {desc}")
    else:
        config = re.sub(r"^(title\s*=.*)$", lambda m: m.group(1) + "\ndescription = " + desc, config, count=1, flags=re.MULTILINE)
    replace_one(r"^  emoji\s*=.*$", f"  emoji = {ts(prop_text(props, 'サイドバー絵文字') or '🖥️')}")
    replace_one(r"^  subtitle\s*=.*$", f"  subtitle = {ts(prop_text(props, 'サイドバー説明'))}")
    replace_one(r"(?s)(\[params\.sidebar\.avatar\]\n  enabled\s*=)[^\n]*", lambda m: m.group(1) + f" {str(avatar_src is not None).lower()}")
    replace_one(r"(?s)(\[params\.sidebar\.avatar\].*?\n  local\s*=)[^\n]*", lambda m: m.group(1) + " true")
    replace_one(r"(?s)(\[params\.sidebar\.avatar\].*?\n  src\s*=)[^\n]*", lambda m: m.group(1) + f" {ts(avatar_src or 'img/notion-avatar.png')}")
    replace_one(r"^  since\s*=.*$", f"  since = {prop_number(props, 'フッター開始年', 2026)}")
    replace_one(r"^  default\s*=.*$", f"  default = {ts(prop_select(props, 'テーマ配色') or 'auto')}")
    replace_one(r"^  toc\s*=.*$", f"  toc = {str(prop_checkbox(props, '目次を表示')).lower()}")
    replace_one(r"^  readingTime\s*=.*$", f"  readingTime = {str(prop_checkbox(props, '読了時間を表示')).lower()}")
    replace_one(r"(?<=\[params\.comments\]\n)  enabled\s*=.*$", f"  enabled = {str(prop_checkbox(props, 'コメントを表示')).lower()}")
    path.write_text(config, encoding="utf-8")
    print("Applied Notion site settings to hugo.toml.")

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Notion's data-source query endpoint has intermittently returned
    # invalid_request_url for valid IDs. The Search API is stable; retrieve
    # accessible pages and keep only rows whose parent is this data source.
    discovered = list(paginated("/search", {
        "page_size": 100,
        "filter": {"property": "object", "value": "page"},
    }))
    pages = [
        page for page in discovered
        if (page.get("parent") or {}).get("data_source_id") == DATA_SOURCE_ID
        or (page.get("parent") or {}).get("database_id") == DATA_SOURCE_ID
    ]
    print(f"Found {len(pages)} page(s) in the Azelqo Notion data source.")
    if not pages:
        raise RuntimeError("No pages were returned for the configured Notion data source; refusing to delete existing posts.")
    keep: set[str] = set()
    published = 0
    settings = None
    for page in pages:
        props = page.get("properties", {})
        status = prop_select(props, "公開状態＊")
        if status == "設定":
            settings = props
            continue
        if status != "公開": continue
        title = prop_text(props, "記事タイトル＊", "title").strip()
        if not title:
            print(f"Skip page {page['id']}: 記事タイトル＊ is empty")
            continue
        slug = prop_text(props, "URLスラッグ").strip() or slugify(title)
        slug = re.sub(r"[^a-zA-Z0-9ぁ-んァ-ン一-龥_-]+", "-", slug).strip("-")
        filename = f"{slug}.md"
        keep.add(filename)
        # Use Notion page last_edited_time so every content or property edit updates the displayed article date.
        edited_at = page.get("last_edited_time") or page.get("created_time") or dt.datetime.now(dt.timezone.utc).isoformat()
        date_value = dt.datetime.fromisoformat(edited_at.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
        description = prop_text(props, "記事の概要").strip()
        image_url = prop_text(props, "アイキャッチ画像URL").strip()
        image_alt = prop_text(props, "アイキャッチ画像alt").strip()
        if image_url:
            parsed_image = urllib.parse.urlparse(image_url)
            if parsed_image.scheme != "https" or parsed_image.netloc not in {"azelqo.github.io", "images.pexels.com"}:
                raise RuntimeError(f"Unsupported アイキャッチ画像URL: {image_url}")
            if not parsed_image.path.lower().endswith((".svg", ".png", ".jpg", ".jpeg", ".webp")):
                raise RuntimeError(f"Unsupported アイキャッチ画像URL extension: {image_url}")
        tags = prop_multi(props, "タグ")
        categories = prop_multi(props, "カテゴリー")
        print(f"Reading Notion article: {title} ({page['id']})")
        body = get_page_markdown(page["id"])
        front = [
            "---", f"title: {yaml_string(title)}", f"description: {yaml_string(description)}",
            f"date: {yaml_string(date_value)}", f"lastmod: {yaml_string(date_value)}",
            'author: "Azelqo"', "draft: false", "categories:",
        ]
        front.extend([f"  - {yaml_string(x)}" for x in categories] or ['  - "メモ"'])
        if image_url:
            front.append(f"image: {yaml_string(image_url)}")
        if image_alt:
            front.append(f"imageAlt: {yaml_string(image_alt)}")
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
