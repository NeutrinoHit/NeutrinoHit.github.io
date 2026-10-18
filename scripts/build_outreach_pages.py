#!/usr/bin/env python3
"""Write the outreach, films and interviews pages of the site from outreach.catalog.yml.

Each page is a list of groups; a group is one lecture (its title opens the main
material, the formats follow it) or a series whose entries are listed under the
group head, one line per entry: title, short note, format links. There are no
previews and no second copy of the material below a list of tiles, so every
material is one click away from the page. Each group keeps the anchor the old
page had (in-a-nutshell, neutrino-telescopes, ...), so links and the
"← Course" button of the slides still land on it.
The interviews list is read from the front matter of ru/interviews/*.qmd (one
page per interview, article or programme: title, title-en, group, kind, outlet,
outlet-en, published), so a new interview is one new page there.

The pages are reproducible outputs: edit the catalog, then run

  python scripts/build_outreach_pages.py           # write the pages
  python scripts/build_outreach_pages.py --check   # exit 1 if a page is stale
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "outreach.catalog.yml"
LANGS = ("ru", "en")
PAGES = {"outreach": "outreach.qmd", "cinema": "cinema.qmd", "interviews": "interviews.qmd"}

T = {
    "ru": {
        "kinds": {"slides": "Слайды", "pdf": "PDF", "video": "Видео", "applet": "Апплет",
                  "game": "Игра", "text": "Читать", "audio": "Аудио"},
        "lang_mark": {"en": "англ."},
        "formats": "Форматы",
    },
    "en": {
        "kinds": {"slides": "Slides", "pdf": "PDF", "video": "Video", "applet": "Applet",
                  "game": "Game", "text": "Read", "audio": "Audio"},
        "lang_mark": {"en": "EN"},
        "formats": "Formats",
    },
}


def e(text: str) -> str:
    return html.escape(str(text), quote=True)


def tr(value, lang: str) -> str:
    """A text that is either one string or a {ru, en} pair."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("ru") or value.get("en") or ""
    return value or ""


def href(item: dict, lang: str, key: str = "href", depth: int = 1) -> str:
    """A link from a page <depth> folders below the site root; site paths start with '/'."""
    path = item.get(f"{key}_en") if lang == "en" and item.get(f"{key}_en") else item[key]
    return "/".join([".."] * depth) + path if path.startswith("/") else path


def external(url: str) -> str:
    return ' rel="noopener"' if url.startswith("http") else ""


def formats(links: list[dict], lang: str, label: str) -> str:
    parts = []
    for link in links:
        url = href(link, lang)
        text = tr(link.get("label"), lang) or T[lang]["kinds"][link["kind"]]
        cls = f"outreach-format is-{link['kind']}"
        parts.append(f'<a class="{cls}" href="{e(url)}"{external(url)}>{e(text)}</a>')
    return f'<span class="outreach-formats" aria-label="{e(label)}">{"".join(parts)}</span>'


def lang_mark(entry: dict, lang: str) -> str:
    mark = T[lang]["lang_mark"].get(entry.get("lang", "ru"))
    return f'<span class="outreach-lang">{e(mark)}</span>' if mark else ""


def title_link(entry: dict, lang: str, cls: str) -> str:
    url = href(entry["links"][0], lang)
    return f'<a class="{cls}" href="{e(url)}"{external(url)}>{e(tr(entry["title"], lang))}</a>'


def entries_of(group: dict, lang: str) -> list[dict]:
    """On the English page the entries in English come first."""
    items = group.get("items", [])
    return sorted(items, key=lambda it: it.get("lang", "ru") != "en") if lang == "en" else items


def entry_line(entry: dict, lang: str) -> str:
    title = title_link(entry, lang, "outreach-entry-title")
    note = tr(entry.get("note"), lang)
    meta = lang_mark(entry, lang) + (f'<span class="outreach-entry-note">{e(note)}</span>' if note else "")
    anchor = f' id="{e(entry["id"])}"' if entry.get("id") else ""
    return (f'<li class="outreach-entry"{anchor}><span class="outreach-entry-main">{title}{meta}</span>'
            f'{formats(entry["links"], lang, T[lang]["formats"])}</li>')


def group_block(group: dict, lang: str) -> list[str]:
    anchor = f' id="{e(group["id"])}"' if group.get("id") and group.get("title") else ""
    out = [f'    <div class="outreach-group"{anchor}>']
    if group.get("title"):
        out.append('      <div class="outreach-group-head">')
        if group.get("kind"):
            out.append(f'        <span class="course-tile-status is-ready">{e(tr(group["kind"], lang))}</span>')
        if group.get("links"):
            title = title_link(group, lang, "outreach-group-title")
            out.append(f'        <h2 class="outreach-group-name">{title}{lang_mark(group, lang)}</h2>')
        else:
            out.append(f'        <h2 class="outreach-group-name">{e(tr(group["title"], lang))}</h2>')
        if group.get("summary"):
            out.append(f'        <p class="outreach-group-text">{e(tr(group["summary"], lang))}</p>')
        if group.get("links"):
            out.append("        " + formats(group["links"], lang, T[lang]["formats"]))
        out.append("      </div>")
    entries = entries_of(group, lang)
    if entries:
        out.append('      <ul class="outreach-entries">')
        out += ["        " + entry_line(entry, lang) for entry in entries]
        out.append("      </ul>")
    if group.get("all"):
        url = href(group["all"], lang)
        out.append(f'      <a class="outreach-all" href="{e(url)}">{e(tr(group["all"]["label"], lang))} →</a>')
    out.append("    </div>")
    return out


def page(section: dict, lang: str, variant: str = "") -> str:
    out = ["---", f'title: "{tr(section["title"], lang)}"']
    if lang == "en":
        out.append("lang: en-US")
    out += ["toc: false", "---", "", "```{=html}", '<div class="lecture-catalog outreach-catalog">',
            f'  <p class="lecture-catalog-lead">{e(tr(section["lead"], lang))}</p>',
            f'  <div class="outreach-list{variant}">']
    for group in section["groups"]:
        out += group_block(group, lang)
    out.append("  </div>")
    if section.get("more"):
        more = section["more"]
        out.append(f'  <p class="outreach-more">{e(tr(more["text"], lang))} '
                   f'<a href="{e(href(more, lang))}">{e(tr(more["label"], lang))}</a>.</p>')
    out += ["</div>", "```", ""]
    return "\n".join(out)


def front_matter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])


def pages_as_entries(section: dict) -> dict:
    """Fill the groups of a section from the front matter of its pages (one page per interview)."""
    pages = []
    for path in sorted((ROOT / section["pages"]).glob("*.qmd")):
        fm = front_matter(path)
        pages.append({
            "title": {"ru": fm["title"], "en": fm.get("title-en", fm["title"])},
            "note": {"ru": fm.get("outlet", ""), "en": fm.get("outlet-en", fm.get("outlet", ""))},
            "links": [{"kind": fm["kind"], "href": f"/{section['pages']}/{path.stem}.html"}],
            "group": fm["group"], "published": str(fm.get("published", "")),
        })
    pages.sort(key=lambda p: p["published"], reverse=True)
    groups = [dict(group, items=[p for p in pages if p["group"] == group["id"]]) for group in section["groups"]]
    return dict(section, groups=groups)


def outputs(catalog: dict, langs=LANGS) -> dict[Path, str]:
    catalog = dict(catalog)
    if catalog.get("interviews", {}).get("pages"):
        catalog["interviews"] = pages_as_entries(catalog["interviews"])
    return {ROOT / lang / name: page(catalog[key], lang)
            for lang in langs for key, name in PAGES.items() if catalog.get(key, {}).get("groups")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale pages, write nothing")
    parser.add_argument("--lang", choices=LANGS, help="only the pages of this language")
    args = parser.parse_args()

    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    stale = []
    for path, text in outputs(catalog, (args.lang,) if args.lang else LANGS).items():
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(path.relative_to(ROOT))
        if not args.check:
            path.write_text(text, encoding="utf-8")
    for path in stale:
        print(("stale  " if args.check else "wrote  ") + str(path))
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
