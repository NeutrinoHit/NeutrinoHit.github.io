#!/usr/bin/env python3
"""Build the Pages site of this media project from media.manifest.json.

Every film is downloaded from its GitHub Release (or taken from a local
content-addressed cache with --from-cache DIR, files named <sha256>.mp4),
checked against the SHA-256 and size of the manifest and written to
_site/<id>/<variant>-v<version>.mp4. The build fails on any mismatch or when
the site would exceed the budget of the manifest. Standard library only.

  python3 scripts/build_site.py [--from-cache DIR] [--out _site]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as response, target.open("wb") as out:
                shutil.copyfileobj(response, out, 1 << 20)
            return
        except OSError as error:
            if attempt == 3:
                raise SystemExit(f"download failed: {url}: {error}")
            time.sleep(5 * (attempt + 1))


def index_page(manifest: dict, total: int) -> str:
    rows = []
    for film in manifest["media"]:
        title = html.escape((film.get("title") or {}).get("en") or film["id"])
        rows.append(f'<tr><td><a href="{html.escape(film["file"])}">{html.escape(film["file"])}</a></td>'
                    f'<td>{title}</td><td>{film["width"]}×{film["height"]}</td>'
                    f'<td>{film["duration_s"]:.0f} s</td><td>{film["bytes"] / 1e6:.1f} MB</td></tr>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(manifest["title"])}</title>
<style>body{{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:24px auto;max-width:1000px;padding:0 16px;color:#25313a;background:#f5f7fd}}
table{{border-collapse:collapse;width:100%}}td{{padding:3px 8px;border-bottom:1px solid #dde3ee}}a{{color:#1f6f8b}}</style></head>
<body><h1>{html.escape(manifest["title"])}</h1>
<p>Films of <a href="https://neutrinohit.github.io/">NeutrinoHit</a> used by its gallery, QR pages, lectures and talks.
{len(manifest["media"])} files, {total / 1e6:.1f} MB. Addresses are permanent: a new render gets a new version.</p>
<table>{"".join(rows)}</table></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--from-cache", type=Path, help="directory with <sha256>.mp4 copies instead of downloads")
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    args = parser.parse_args()

    manifest = json.loads((ROOT / "media.manifest.json").read_text(encoding="utf-8"))
    total = sum(film["bytes"] for film in manifest["media"])
    if total > manifest["budget_bytes"]:
        raise SystemExit(f"{total} bytes exceed the budget {manifest['budget_bytes']}")
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for film in manifest["media"]:
        target = out / film["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if args.from_cache:
            source = args.from_cache / f'{film["sha256"]}.mp4'
            if not source.is_file():
                raise SystemExit(f"not in the cache: {film['file']} ({source.name})")
            shutil.copyfile(source, target)
        else:
            download(film["url"], target)
        size = target.stat().st_size
        if size != film["bytes"] or sha256(target) != film["sha256"]:
            raise SystemExit(f"{film['file']}: size or SHA-256 differs from the manifest")
        print(f"ok {film['file']}  {size / 1e6:.1f} MB")
    (out / "index.html").write_text(index_page(manifest, total), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    shutil.copyfile(ROOT / "media.manifest.json", out / "media.manifest.json")
    print(f"{manifest['home']}: {len(manifest['media'])} films, {total / 1e6:.1f} MB "
          f"({100 * total / 1e9:.0f}% of the 1 GB Pages limit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
