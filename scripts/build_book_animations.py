#!/usr/bin/env python3
"""Build the QR landing pages for the animations printed in the QFT book.

Source of truth: book-animations.catalog.json.  Each item gets a permanent
page https://neutrinohit.github.io/qr/<id>/ (the address encoded in the book's
QR code), a normalized MP4 and a poster in assets/book-animations/, and an
entry in the index page qr/index.html.

Hosting modes (field "hosting" of an item):
  self      the animation is published here (needs "media.source")
  external  rights are not ours: the page credits the author and links out
  pending   the animation is not available yet: the page says so

An item with "status": "proposed" is validated but not published (no page, no
index entry, no QR url) until the status is removed; --include-proposed builds
it anyway for a local preview.  An item may reuse a video that already lives on
the site (media.site_asset) instead of copying it.

Local sources live in not-to-commit/book-animations-src/ (git-ignored);
published outputs are committed.  To publish an item that is currently
"external" or "pending" once the rights are cleared, set hosting to "self"
and make sure media.source exists in the source directory.

Usage:
  python scripts/build_book_animations.py            # build everything
  python scripts/build_book_animations.py --check    # validate only
  python scripts/build_book_animations.py --urls     # "url, qr_file" lines
  python scripts/build_book_animations.py --include-proposed   # local preview only
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SITE_ROOT = Path(__file__).resolve().parents[1]
CATALOG = SITE_ROOT / "book-animations.catalog.json"
SOURCE_DIR = SITE_ROOT / "not-to-commit" / "book-animations-src"
ASSET_DIR = SITE_ROOT / "assets" / "book-animations"
OUT_DIR = SITE_ROOT / "qr"

HOSTING = ("self", "external", "pending")
MAX_SIDE = 1280
COPY_LIMIT_MB = 3.0


# ---------------------------------------------------------------- catalog

def load_catalog() -> dict[str, Any]:
    with CATALOG.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
    book = item["book"]
    return (book["volume"], book["chapter"], item["id"])


def validate(catalog: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    seen_ids: set[str] = set()
    seen_slugs: set[str] = set()
    codes: set[str] = set()
    for item in catalog["items"]:
        ident = item.get("id", "?")
        if not (ident.isdigit() and len(ident) == 4):
            problems.append(f"{ident}: id must be four digits")
        if ident in seen_ids:
            problems.append(f"{ident}: duplicate id")
        seen_ids.add(ident)
        slug = item.get("slug", "")
        if slug in seen_slugs:
            problems.append(f"{ident}: duplicate slug {slug}")
        seen_slugs.add(slug)
        for code in item.get("legacy_codes", []):
            if code in codes or code in seen_ids:
                problems.append(f"{ident}: legacy code {code} is not unique")
            codes.add(code)
        for key in ("title", "caption"):
            for lang in ("ru", "en"):
                if not item.get(key, {}).get(lang):
                    problems.append(f"{ident}: missing {key}.{lang}")
        hosting = item.get("hosting")
        if hosting not in HOSTING:
            problems.append(f"{ident}: hosting must be one of {HOSTING}")
        credit = item.get("credit", {})
        if hosting == "self":
            media = item.get("media", {})
            if media.get("site_asset"):
                if not (SITE_ROOT / media["site_asset"]).is_file():
                    problems.append(f"{ident}: missing site asset {media['site_asset']}")
            else:
                source = SOURCE_DIR / media.get("source", "")
                published = ASSET_DIR / f"{ident}.mp4"
                if not source.is_file() and not published.is_file():
                    problems.append(f"{ident}: no media source {source.name or '(unset)'}")
            if not has_text(credit.get("author")):
                problems.append(f"{ident}: self-hosted item needs credit.author")
        if hosting == "external":
            url = item.get("external_url", "")
            if urlparse(url).scheme != "https":
                problems.append(f"{ident}: external_url must be https")
    return problems


# ------------------------------------------------------------------ media

def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def probe(path: Path) -> dict[str, Any]:
    out = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height:format=duration",
        "-of", "json", str(path),
    ]).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    return {
        "codec": stream["codec_name"],
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(data["format"].get("duration") or 0.0),
    }


def stale(source: Path, target: Path, force: bool) -> bool:
    return force or not target.exists() or source.stat().st_mtime > target.stat().st_mtime


def build_media(item: dict[str, Any], force: bool) -> None:
    ident = item["id"]
    site_asset = item["media"].get("site_asset")
    source = SITE_ROOT / site_asset if site_asset else SOURCE_DIR / item["media"]["source"]
    movie = ASSET_DIR / f"{ident}.mp4"
    poster = ASSET_DIR / f"{ident}.jpg"
    if not source.is_file():
        return  # outputs are committed; sources are optional
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    info = probe(source)

    if not site_asset and stale(source, movie, force):
        tmp = movie.with_suffix(".tmp.mp4")
        is_small_h264 = (
            source.suffix.lower() == ".mp4"
            and info["codec"] == "h264"
            and source.stat().st_size <= COPY_LIMIT_MB * 1024 * 1024
            and max(info["width"], info["height"]) <= MAX_SIDE
        )
        if is_small_h264:
            command = ["ffmpeg", "-y", "-v", "error", "-i", str(source),
                       "-c", "copy", "-movflags", "+faststart", str(tmp)]
        else:
            scale = (f"scale='if(gt(iw,ih),min({MAX_SIDE},iw),-2)':"
                     f"'if(gt(iw,ih),-2,min({MAX_SIDE},ih))':flags=lanczos,"
                     "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p")
            command = ["ffmpeg", "-y", "-v", "error", "-i", str(source),
                       "-vf", scale, "-c:v", "libx264", "-preset", "slow",
                       "-crf", str(item["media"].get("crf", 26)), "-c:a", "aac", "-b:a", "96k",
                       "-movflags", "+faststart", str(tmp)]
        run(command)
        tmp.replace(movie)

    if stale(source, poster, force):
        at = float(item["media"].get("poster_time", 0.5))
        if info["duration"]:
            at = min(at, info["duration"] * 0.5)
        tmp = poster.with_suffix(".tmp.jpg")
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(source),
             "-frames:v", "1", "-vf", "scale='min(960,iw)':-2", "-q:v", "3", str(tmp)])
        tmp.replace(poster)


# ------------------------------------------------------------------- html

CSS = """
:root{--bg:#f5f7fd;--card:#fff;--text:#25313a;--muted:#53616f;--accent:#1f6f8b;--border:rgba(43,67,91,.16);--shadow:0 8px 24px rgba(43,67,91,.12);--media:#000}
@media (prefers-color-scheme:dark){:root{--bg:#10161c;--card:#18212a;--text:#e6edf3;--muted:#9fb0bf;--accent:#6cc0dc;--border:rgba(160,190,220,.22);--shadow:none}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:17px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-text-size-adjust:100%}
a{color:var(--accent)}
.wrap{max-width:780px;margin:0 auto;padding:12px max(16px,env(safe-area-inset-right)) 40px max(16px,env(safe-area-inset-left))}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:14px;color:var(--muted);padding:6px 0 10px}
.top a{color:inherit;text-decoration:none}
.lang{display:inline-flex;border:1px solid var(--border);border-radius:7px;overflow:hidden}
.lang button{font:inherit;font-size:13px;border:0;background:transparent;color:var(--muted);padding:4px 10px;cursor:pointer}
html[data-lang=ru] .lang [data-set=ru],html[data-lang=en] .lang [data-set=en]{background:var(--accent);color:var(--card)}
h1{font-size:1.45rem;line-height:1.25;margin:.2em 0 .6em}
.stage{margin:0 0 14px;background:var(--media);border-radius:8px;overflow:hidden;box-shadow:var(--shadow);text-align:center}
.stage video{display:block;width:100%;height:auto;max-height:72vh;margin:0 auto;object-fit:contain}
.tools{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0 0 14px;font-size:14px;color:var(--muted)}
.tools button,.btn{font:inherit;font-size:14px;border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:7px;padding:5px 11px;cursor:pointer;text-decoration:none}
.tools button[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:var(--card)}
.btn.primary{display:inline-block;background:var(--accent);border-color:var(--accent);color:var(--card);padding:10px 18px;font-size:16px}
.caption{margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;margin:0 0 16px}
.card p{margin:.2em 0 .8em}
dl.meta{margin:0;display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:15px}
dl.meta dt{color:var(--muted)}
dl.meta dd{margin:0}
.nav{display:flex;justify-content:space-between;gap:12px;font-size:15px;margin:22px 0 0}
.nav a{max-width:48%}
footer{margin-top:26px;font-size:13px;color:var(--muted)}
html[data-lang=ru] [lang=en],html[data-lang=en] [lang=ru]{display:none!important}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:0;padding:0;list-style:none}
.grid a{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;height:100%}
.grid img,.grid .ph{display:block;width:100%;aspect-ratio:16/10;object-fit:cover;background:var(--media)}
.grid .ph{display:flex;align-items:center;justify-content:center;color:#9fb0bf;font-size:13px}
.grid .t{padding:8px 11px 10px;font-size:15px;line-height:1.35}
.grid small{display:block;color:var(--muted);font-size:12.5px;margin-top:3px}
h2{font-size:1.1rem;margin:1.6em 0 .6em;color:var(--muted);font-weight:600}
""".strip()

LANG_JS = """
(function(){var d=document.documentElement,l,q;try{q=new URLSearchParams(location.search).get('lang');l=q||localStorage.getItem('nh-lang')}catch(e){}
if(l!=='ru'&&l!=='en'){l=((navigator.language||'ru').toLowerCase().indexOf('ru')===0)?'ru':'en'}
d.setAttribute('data-lang',l);d.lang=l})();
""".strip()

LANG_BAR_JS = """
(function(){var d=document.documentElement;function apply(l,save){d.setAttribute('data-lang',l);d.lang=l;
var t=d.getAttribute('data-title-'+l);if(t)document.title=t;
if(save){try{localStorage.setItem('nh-lang',l)}catch(e){}}}
apply(d.getAttribute('data-lang'),false);
document.querySelectorAll('.lang button').forEach(function(b){b.addEventListener('click',function(){apply(b.getAttribute('data-set'),true)})});
})();
""".strip()

PLAYER_JS = """
(function(){var v=document.getElementById('v');if(!v)return;
if(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches){v.removeAttribute('autoplay');v.pause()}
var bs=document.querySelectorAll('[data-rate]');bs.forEach(function(b){b.addEventListener('click',function(){
v.playbackRate=parseFloat(b.getAttribute('data-rate'));bs.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
if(v.paused)v.play().catch(function(){})})})})();
""".strip()


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def bi(pair: dict[str, str]) -> str:
    return (f'<span lang="ru">{esc(pair["ru"])}</span>'
            f'<span lang="en">{esc(pair["en"])}</span>')


def bi_raw(ru: str, en: str) -> str:
    return f'<span lang="ru">{ru}</span><span lang="en">{en}</span>'


def text_or_pair(value: Any) -> str:
    """A plain string, or a {ru, en} pair, as bilingual markup."""
    return bi(value) if isinstance(value, dict) else esc(value)


def has_text(value: Any) -> bool:
    return bool(value and (value.get("ru") if isinstance(value, dict) else value))


def host_of(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def page_url(catalog: dict[str, Any], ident: str = "") -> str:
    return f'{catalog["base_url"]}{catalog["qr_path"]}{ident + "/" if ident else ""}'


def movie_path(item: dict[str, Any]) -> str:
    """Site-root-relative path of the video shown on the page."""
    return item["media"].get("site_asset") or f'assets/book-animations/{item["id"]}.mp4'


def chapter_ref(item: dict[str, Any]) -> str:
    book = item["book"]
    title = book["chapter_title"]
    return bi_raw(
        f'Том {book["volume"]}, гл. {book["chapter"]} «{esc(title["ru"])}»',
        f'Volume {book["volume"]}, Chapter {book["chapter"]} “{esc(title["en"])}”',
    )


def head(catalog: dict[str, Any], title: dict[str, str], description: dict[str, str],
         canonical: str, og_image: str = "", extra: str = "") -> str:
    ru_title = f'{title["ru"]} — NeutrinoHit'
    en_title = f'{title["en"]} — NeutrinoHit'
    image = f'<meta property="og:image" content="{esc(og_image)}">\n' if og_image else ""
    return f"""<!doctype html>
<html lang="ru" data-lang="ru" data-title-ru="{esc(ru_title)}" data-title-en="{esc(en_title)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(ru_title)}</title>
<meta name="description" content="{esc(description["ru"])}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title["ru"])}">
<meta property="og:description" content="{esc(description["ru"])}">
<meta property="og:url" content="{esc(canonical)}">
{image}{extra}<script>{LANG_JS}</script>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
"""


def topbar(prefix: str) -> str:
    return f"""<div class="top">
<a href="{prefix}">{bi_raw("← Все анимации книги", "← All animations of the book")}</a>
<span class="lang" role="group" aria-label="Language"><button type="button" data-set="ru">RU</button><button type="button" data-set="en">EN</button></span>
</div>
"""


def footer(catalog: dict[str, Any]) -> str:
    book = catalog["book"]
    author = bi_raw(esc(book["author"]["ru"]), esc(book["author"]["en"]))
    return f"""<footer>
<p>{bi_raw("Анимация к книге", "Animation for the book")} <a href="{esc(book["page"]["ru"])}" lang="ru">«{esc(book["title"]["ru"])}»</a><a href="{esc(book["page"]["en"])}" lang="en">“{esc(book["title"]["en"])}”</a>, {author} · <a href="/">NeutrinoHit</a></p>
</footer>
</div>
<script>{LANG_BAR_JS}</script>
<script defer src="https://neutrinohit.github.io/assets/analytics/cloudflare-web-analytics.js"></script>
</body>
</html>
"""


def credit_block(item: dict[str, Any]) -> str:
    credit = item.get("credit", {})
    rows: list[tuple[str, str]] = []
    rows.append((bi_raw("В книге", "In the book"), chapter_ref(item)))
    if has_text(credit.get("author")):
        work = f' — {text_or_pair(credit["work"])}' if has_text(credit.get("work")) else ""
        rows.append((bi_raw("Автор", "Author"), f'{text_or_pair(credit["author"])}{work}'))
    if credit.get("source_url"):
        label = credit.get("source_label") or host_of(credit["source_url"])
        rows.append((bi_raw("Источник", "Source"),
                     f'<a href="{esc(credit["source_url"])}" rel="noopener">{esc(label)}</a>'))
    if credit.get("code_url"):
        rows.append((bi_raw("Код", "Code"),
                     f'<a href="{esc(credit["code_url"])}" rel="noopener">GitHub</a>'))
    if credit.get("license"):
        text = esc(credit["license"])
        if credit.get("license_url"):
            text = f'<a href="{esc(credit["license_url"])}" rel="noopener">{text}</a>'
        rows.append((bi_raw("Лицензия", "License"), text))
    if credit.get("note"):
        rows.append((bi_raw("Примечание", "Note"), bi(credit["note"])))
    for extra in credit.get("see_also", []):
        rows.append((bi_raw("См. также", "See also"),
                     f'<a href="{esc(extra["url"])}" rel="noopener">{esc(extra["label"])}</a>'))
    if item.get("gallery"):
        section, entry = item["gallery"].split("/")
        rows.append((bi_raw("Галерея", "Gallery"),
                     f'<a href="/ru/animations.html#animation-{esc(section)}-{esc(entry)}">'
                     f'{bi_raw("Все анимации NeutrinoHit", "All NeutrinoHit animations")}</a>'))
    body = "\n".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    return f'<div class="card"><dl class="meta">\n{body}\n</dl></div>\n'


def neighbours(items: list[dict[str, Any]], index: int) -> str:
    left = right = "<span></span>"
    if index > 0:
        prev = items[index - 1]
        left = f'<a href="../{prev["id"]}/">← {bi_raw("Предыдущая", "Previous")}: {bi(prev["title"])}</a>'
    if index < len(items) - 1:
        nxt = items[index + 1]
        right = f'<a href="../{nxt["id"]}/">{bi_raw("Следующая", "Next")}: {bi(nxt["title"])} →</a>'
    return f'<nav class="nav">{left}{right}</nav>\n'


def render_item(catalog: dict[str, Any], items: list[dict[str, Any]], index: int) -> str:
    item = items[index]
    ident = item["id"]
    hosting = item["hosting"]
    url = page_url(catalog, ident)
    poster_exists = (ASSET_DIR / f"{ident}.jpg").is_file()
    og_image = f'{catalog["base_url"]}/assets/book-animations/{ident}.jpg' if (
        hosting == "self" and poster_exists) else ""
    page = head(catalog, item["title"], item["caption"], url, og_image)
    page += topbar("../")
    page += f'<h1>{bi(item["title"])}</h1>\n'

    if hosting == "self":
        poster = f' poster="../../assets/book-animations/{ident}.jpg"' if poster_exists else ""
        movie = f"../../{movie_path(item)}"
        page += f"""<div class="stage"><video id="v" controls playsinline loop muted autoplay preload="metadata"{poster}>
<source src="{movie}" type="video/mp4">
</video></div>
<div class="tools" aria-label="{esc("Скорость / Speed")}">
<span>{bi_raw("Скорость", "Speed")}:</span>
<button type="button" data-rate="0.25" aria-pressed="false">0.25×</button>
<button type="button" data-rate="0.5" aria-pressed="false">0.5×</button>
<button type="button" data-rate="1" aria-pressed="true">1×</button>
<button type="button" data-rate="2" aria-pressed="false">2×</button>
<a class="btn" href="{movie}" download>{bi_raw("Скачать MP4", "Download MP4")}</a>
</div>
"""
    elif hosting == "external":
        host = esc(host_of(item["external_url"]))
        page += f"""<div class="card">
<p>{bi_raw("Эта анимация размещена на сайте правообладателя.", "This animation is published on the rights holder's website.")}</p>
<p><a class="btn primary" href="{esc(item["external_url"])}" rel="noopener">{bi_raw("Смотреть анимацию", "Watch the animation")} ({host})</a></p>
</div>
"""
    else:
        page += f"""<div class="card">
<p>{bi_raw("Эта анимация скоро появится на странице. Загляните позже.", "This animation will appear here soon. Please check back later.")}</p>
</div>
"""

    page += f'<p class="caption">{bi(item["caption"])}</p>\n'
    page += credit_block(item)
    page += neighbours(items, index)
    page += footer(catalog)
    if hosting == "self":
        page = page.replace("</body>", f"<script>{PLAYER_JS}</script>\n</body>")
    return page


def render_alias(catalog: dict[str, Any], item: dict[str, Any], code: str) -> str:
    target = page_url(catalog, item["id"])
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(item["title"]["ru"])} — NeutrinoHit</title>
<meta http-equiv="refresh" content="0; url=../{item["id"]}/">
<link rel="canonical" href="{esc(target)}">
<meta name="robots" content="noindex">
<script>location.replace("../{item["id"]}/"+location.search+location.hash)</script>
</head>
<body><p><a href="../{item["id"]}/">{esc(item["title"]["ru"])}</a></p></body>
</html>
"""


def render_index(catalog: dict[str, Any], items: list[dict[str, Any]]) -> str:
    title = {"ru": "Анимации книги", "en": "Animations of the book"}
    desc = {
        "ru": "Все анимации, на которые ведут QR-коды книги «Квантовая теория поля для экспериментаторов и не только».",
        "en": "All animations linked by the QR codes of the book “Quantum Field Theory for Experimentalists and Beyond”.",
    }
    page = head(catalog, title, desc, page_url(catalog))
    page += f"""<div class="top"><a href="/">NeutrinoHit</a>
<span class="lang" role="group" aria-label="Language"><button type="button" data-set="ru">RU</button><button type="button" data-set="en">EN</button></span></div>
<h1>{bi(title)}</h1>
<p class="caption">{bi(desc)}</p>
"""
    current = None
    for item in items:
        group = (item["book"]["volume"], item["book"]["chapter"])
        if group != current:
            if current is not None:
                page += "</ul>\n"
            current = group
            page += f'<h2>{chapter_ref(item)}</h2>\n<ul class="grid">\n'
        ident = item["id"]
        if item["hosting"] == "self" and (ASSET_DIR / f"{ident}.jpg").is_file():
            thumb = f'<img src="../assets/book-animations/{ident}.jpg" alt="" loading="lazy">'
        else:
            thumb = f'<div class="ph">{bi_raw("на сайте автора", "on the author’s site") if item["hosting"] == "external" else bi_raw("скоро", "soon")}</div>'
        page += (f'<li><a href="{ident}/">{thumb}<div class="t">{bi(item["title"])}'
                 f'<small>QR {ident}</small></div></a></li>\n')
    page += "</ul>\n"
    page += footer(catalog)
    return page


def write_if_changed(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def build_pages(catalog: dict[str, Any], items: list[dict[str, Any]],
                out_dir: Path) -> list[Path]:
    OUT = out_dir
    written: list[Path] = []
    for index, item in enumerate(items):
        path = OUT / item["id"] / "index.html"
        if write_if_changed(path, render_item(catalog, items, index)):
            written.append(path)
        for code in item.get("legacy_codes", []):
            alias = OUT / code / "index.html"
            if write_if_changed(alias, render_alias(catalog, item, code)):
                written.append(alias)
    if write_if_changed(OUT / "index.html", render_index(catalog, items)):
        written.append(OUT / "index.html")
    manifest = {
        item["id"]: {
            "url": page_url(catalog, item["id"]),
            "slug": item["slug"],
            "hosting": item["hosting"],
            "qr_file": item.get("qr_file"),
            "legacy_codes": item.get("legacy_codes", []),
        }
        for item in items
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if write_if_changed(OUT / "manifest.json", text):
        written.append(OUT / "manifest.json")
    return written


# ------------------------------------------------------------------- main

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="validate the catalog only")
    parser.add_argument("--urls", action="store_true",
                        help='print "url, qr_file" lines for pyplots/qrcodes/urls.txt')
    parser.add_argument("--force", action="store_true", help="re-encode all media")
    parser.add_argument("--skip-media", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help="where to write the pages (default: qr/)")
    parser.add_argument("--include-proposed", action="store_true",
                        help="also build items with status \"proposed\" (local preview only)")
    args = parser.parse_args()

    catalog = load_catalog()
    problems = validate(catalog)
    if problems:
        print("Catalog problems:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if args.include_proposed and args.out_dir.resolve() == OUT_DIR.resolve():
        print("--include-proposed needs --out-dir elsewhere (e.g. a scratch directory "
              "whose assets/ points to this site's assets/)", file=sys.stderr)
        return 1
    visible = [i for i in catalog["items"]
               if args.include_proposed or i.get("status", "published") == "published"]
    items = sorted(visible, key=sort_key)

    if args.urls:
        for item in sorted(visible, key=lambda i: i["id"]):
            print(f'{page_url(catalog, item["id"])}, {item["qr_file"]}')
        return 0
    if args.check:
        proposed = len(catalog["items"]) - len(
            [i for i in catalog["items"] if i.get("status", "published") == "published"])
        print(f"OK: {len(catalog['items'])} items ({proposed} proposed)")
        return 0

    if not args.skip_media:
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            print("ffmpeg/ffprobe not found; use --skip-media", file=sys.stderr)
            return 1
        for item in items:
            if item["hosting"] == "self":
                build_media(item, args.force)

    written = build_pages(catalog, items, args.out_dir)
    for item in items:
        flag = "  [proposed]" if item.get("status") == "proposed" else ""
        print(f'{item["id"]}  {item["hosting"]:8}  {item["slug"]}{flag}')
    print(f"Wrote {len(written)} file(s) under {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
