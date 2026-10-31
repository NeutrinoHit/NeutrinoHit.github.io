#!/usr/bin/env python3
"""Shared films in a NeutrinoHit project (media.lock.json): prune the site, build an offline bundle.

  media.py prune [SITE]
      delete from the rendered site the local copies that live films replace
      (run after every render by prune.py, the project's post-render script)
  media.py offline PAGE.html [PAGE.html ...] --out DIR [--site _site] [--cache DIR]
                   [--mathjax DIR] [--download]
      a portable folder with the selected pages, their resources and one copy of
      every film they show (media/<sha256>.mp4); start.command serves it locally

Standard library only; the canonical copy is neutrinohit-map/assets/media/_extensions/.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("QUARTO_PROJECT_DIR") or Path.cwd())
SITE_URL = "https://neutrinohit.github.io"
FILM = re.compile(r'(?:https://neutrinohit\.github\.io)?(/media-[a-z]+/[a-z0-9-]+/[a-z0-9-]+-v\d+\.mp4)')
REFS = re.compile(r'\b(?:src|href|poster|data-src|data-background-video|data-background-image|'
                  r'data-background|data-poster|data-src-ru|data-src-en)="([^"#?]+)')
CSS_URL = re.compile(r'url\(\s*["\']?([^"\')#?]+)')
MATHJAX = re.compile(r'https://cdn\.jsdelivr\.net/npm/mathjax@2\.7\.\d+/MathJax\.js')
ANALYTICS = re.compile(r'<script[^>]*cloudflare-web-analytics[^>]*>\s*</script>\s*')
VIDEO_EXT = (".mp4", ".m4v", ".mov", ".webm")

# serve.py of a bundle: a static server with HTTP Range (video seeking), local address only
SERVER = '''import http.server, os, re, sys
class H(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        self.remaining = None
        m = re.fullmatch(r"bytes=(\\d*)-(\\d*)", self.headers.get("Range", ""))
        path = self.translate_path(self.path)
        if not m or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        first = int(m.group(1)) if m.group(1) else max(size - int(m.group(2) or 0), 0)
        last = min(int(m.group(2)), size - 1) if m.group(1) and m.group(2) else size - 1
        f = open(path, "rb"); f.seek(first); self.remaining = last - first + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
        self.send_header("Content-Length", str(self.remaining))
        self.end_headers()
        return f
    def copyfile(self, source, out):
        left = getattr(self, "remaining", None)
        if left is None:
            return super().copyfile(source, out)
        try:
            while left > 0:
                block = source.read(min(1 << 20, left))
                if not block:
                    break
                out.write(block); left -= len(block)
        except (BrokenPipeError, ConnectionResetError):
            pass
os.chdir(os.path.dirname(os.path.abspath(__file__)))
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8790), H).serve_forever()
'''


def lock() -> list[dict]:
    path = ROOT / "media.lock.json"
    return json.loads(path.read_text(encoding="utf-8"))["media"] if path.is_file() else []


def live(entry: dict) -> bool:
    return entry.get("status") == "published" or os.environ.get("NH_MEDIA_PREVIEW") == "1"


def prune(site: Path) -> int:
    removed = freed = 0
    for entry in lock():
        target = site / entry.get("fallback", "")
        if entry.get("fallback") and live(entry) and target.is_file():
            freed += target.stat().st_size
            target.unlink()
            removed += 1
    if removed:
        print(f"shared media: removed {removed} local copies ({freed / 1e6:.1f} MB) from {site}")
    return 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def local_refs(text: str, base: Path, site: Path) -> set[Path]:
    """Files of the site that a page or stylesheet refers to."""
    found: set[Path] = set()
    for ref in REFS.findall(text) + CSS_URL.findall(text):
        ref = html.unescape(ref.strip())
        if not ref or re.match(r"^[a-z][a-z0-9+.-]*:", ref) or ref.startswith("//") or FILM.fullmatch(ref):
            continue
        path = (site / ref.lstrip("/")) if ref.startswith("/") else (base / ref)
        path = path.resolve()
        if path.is_file() and path.is_relative_to(site):
            found.add(path)
    return found


def mathjax_ignore(directory: str, names: list[str]) -> set[str]:
    """Trim MathJax 2.7 to what the CHTML/HTML-CSS output with TeX web fonts loads (about 15 MB of 66)."""
    skip = {n for n in names if n in ("test", "unpacked", "docs") or n.endswith(".md")}
    parts = Path(directory).parts
    if parts[-2:] == ("fonts", "HTML-CSS"):                # web font files: TeX only
        skip |= {n for n in names if n != "TeX"}
    if parts[-3:] == ("fonts", "HTML-CSS", "TeX"):
        skip |= {n for n in names if n in ("png", "otf", "eot", "svg")}
    return skip


def offline(args: argparse.Namespace) -> int:
    site = Path(args.site).resolve()
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    films = {entry["url"]: entry for entry in lock()}
    pages = [(site / page).resolve() for page in args.pages]
    for page in pages:
        if not page.is_file():
            raise SystemExit(f"no such page: {page}")

    # 1. the pages, their directories (interactive figures load files at run time) and site_libs
    files: set[Path] = set()
    if (site / "site_libs").is_dir():
        files |= {p for p in (site / "site_libs").rglob("*") if p.is_file()}
    for page in pages:
        for path in page.parent.rglob("*"):
            if not path.is_file() or path.suffix.lower() in VIDEO_EXT:
                continue
            if path.suffix == ".html" and path.parent == page.parent and path not in pages:
                continue                                    # another deck of the same folder
            files.add(path)
    queue = list(pages)
    while queue:                                            # resources referenced from outside the folders
        current = queue.pop()
        if current.suffix not in (".html", ".css"):
            continue
        for ref in local_refs(current.read_text(encoding="utf-8", errors="replace"), current.parent, site):
            if ref not in files:
                files.add(ref)
                queue.append(ref)
    for path in files:
        target = out / path.relative_to(site)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    # 2. films: one copy per SHA-256, addresses rewritten to the local copy
    (out / "media").mkdir()
    used: dict[str, int] = {}
    external: set[str] = set()
    for page in pages:
        target = out / page.relative_to(site)
        text = target.read_text(encoding="utf-8")

        def local(match: re.Match) -> str:
            entry = films.get(match.group(1))
            if entry is None:
                raise SystemExit(f"{page.name}: {match.group(1)} is not in media.lock.json")
            name = f'{entry["sha256"]}.mp4'
            copy = out / "media" / name
            if not copy.exists():
                source = Path(args.cache) / name if args.cache else None
                if source and source.is_file():
                    shutil.copyfile(source, copy)
                elif args.download:
                    with urllib.request.urlopen(SITE_URL + entry["url"], timeout=600) as r, copy.open("wb") as f:
                        shutil.copyfileobj(r, f, 1 << 20)
                else:
                    raise SystemExit(f"{entry['url']}: not in --cache; add --download to fetch it")
                if sha256(copy) != entry["sha256"]:
                    raise SystemExit(f"{entry['url']}: SHA-256 differs from media.lock.json")
            used[name] = entry["bytes"]
            return os.path.relpath(copy, target.parent)

        text = FILM.sub(local, text)
        text = ANALYTICS.sub("", text)                      # no page statistics from a lecture hall
        if args.mathjax and MATHJAX.search(text):
            vendor = out / "vendor" / "mathjax"
            if not vendor.exists():
                shutil.copytree(args.mathjax, vendor, ignore=mathjax_ignore)
            text = MATHJAX.sub(os.path.relpath(vendor / "MathJax.js", target.parent), text)
        external |= set(re.findall(r'<(?:script|link)[^>]+(?:src|href)="(https?://[^"]+)"', text))
        target.write_text(text, encoding="utf-8")

    # 3. index and launcher (interactive modules and video seeking need HTTP, not file://)
    links = "".join(f'<li><a href="{html.escape(p.relative_to(site).as_posix())}">'
                    f'{html.escape(p.relative_to(site).as_posix())}</a></li>' for p in pages)
    (out / "index.html").write_text(
        f'<!doctype html><meta charset="utf-8"><title>NeutrinoHit offline</title>'
        f'<h1>NeutrinoHit: offline bundle</h1><ul>{links}</ul>', encoding="utf-8")
    (out / "serve.py").write_text(SERVER, encoding="utf-8")
    launcher = out / "start.command"
    launcher.write_text('#!/bin/sh\n# Double-click (macOS) or run: serves this folder on http://127.0.0.1:8790/\n'
                        'cd "$(dirname "$0")"\n'
                        '(sleep 1; open http://127.0.0.1:8790/ 2>/dev/null || xdg-open http://127.0.0.1:8790/) &\n'
                        'exec python3 serve.py 8790\n', encoding="utf-8")
    launcher.chmod(0o755)
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"offline bundle: {len(pages)} page(s), {len(used)} film(s) "
          f"({sum(used.values()) / 1e6:.1f} MB), {total / 1e6:.1f} MB in {out}")
    for url in sorted(external):
        print(f"  still online: {url}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prune")
    p.add_argument("site", nargs="?", default=os.environ.get("QUARTO_PROJECT_OUTPUT_DIR") or "_site")
    p = sub.add_parser("offline")
    p.add_argument("pages", nargs="+", help="pages relative to the site, e.g. talk/lecture.html")
    p.add_argument("--out", required=True)
    p.add_argument("--site", default="_site")
    p.add_argument("--cache", help="directory with <sha256>.mp4 copies (neutrinohit-map/.cache/media)")
    p.add_argument("--mathjax", help="local MathJax 2.7 directory used instead of the CDN")
    p.add_argument("--download", action="store_true", help="fetch films missing from --cache")
    args = parser.parse_args()
    if args.command == "prune":
        site = Path(args.site)
        return prune(site if site.is_absolute() else ROOT / site)
    return offline(args)


if __name__ == "__main__":
    sys.exit(main())
