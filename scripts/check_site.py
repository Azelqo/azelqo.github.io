#!/usr/bin/env python3
"""Dependency-free checks for the generated Hugo site."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve()
errors, warnings = [], []

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()
        self.title = self.description = self.blogposting = self.website = False
        self.in_title = self.in_jsonld = False
        self.jsonld = ""
        self.images_without_alt = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title": self.in_title = True
        if tag == "meta" and a.get("name", "").lower() == "description":
            self.description = bool(a.get("content", "").strip())
        if tag == "script" and a.get("type") == "application/ld+json":
            self.in_jsonld, self.jsonld = True, ""
        if a.get("id"): self.ids.add(a["id"])
        if tag == "img" and "alt" not in a: self.images_without_alt += 1
        for key in ("href", "src", "poster"):
            if a.get(key): self.links.append(a[key])
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        if tag == "script" and self.in_jsonld:
            self.in_jsonld = False
            self.blogposting |= "BlogPosting" in self.jsonld
            self.website |= "WebSite" in self.jsonld
    def handle_data(self, data):
        if self.in_title and data.strip(): self.title = True
        if self.in_jsonld: self.jsonld += data

pages = sorted(ROOT.rglob("*.html"))
if not pages: errors.append("No HTML pages generated")
parsed = {}
for path in pages:
    rel = path.relative_to(ROOT).as_posix()
    p = Parser()
    try: p.feed(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Cannot parse {rel}: {exc}")
        continue
    parsed[rel] = p
    if not p.title: errors.append(f"Missing title: {rel}")
    if rel.startswith("posts/") and rel.endswith("/index.html"):
        if not p.description: errors.append(f"Missing meta description: {rel}")
        if not p.blogposting: errors.append(f"Missing BlogPosting JSON-LD: {rel}")
    if p.images_without_alt: warnings.append(f"{rel}: {p.images_without_alt} image(s) missing alt")

def resolve(source, raw):
    u = urlsplit(raw)
    if u.scheme or u.netloc or not u.path: return None
    decoded = unquote(u.path)
    target = (ROOT / decoded.lstrip("/")) if decoded.startswith("/") else (ROOT / Path(source).parent / decoded)
    target = target.resolve()
    try: target.relative_to(ROOT)
    except ValueError: return None
    if target.is_dir() or not target.suffix: target /= "index.html"
    return target

for source, p in parsed.items():
    for link in p.links:
        target = resolve(source, link)
        if target is not None and not target.exists():
            errors.append(f"Broken local link/resource: {source} -> {link}")

for msg in warnings[:60]: print("WARNING:", msg)
for msg in errors: print("ERROR:", msg)
if errors:
    print(f"FAILED: {len(errors)} error(s), {len(warnings)} accessibility warning(s)")
    sys.exit(1)
print(f"OK: {len(pages)} HTML pages checked; {len(warnings)} accessibility warning(s)")
