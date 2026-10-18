#!/usr/bin/env python3
"""Write the list pages of the site from their catalogs: outreach, films and interviews
(outreach.catalog.yml), research (research.catalog.yml) and modeling (modeling.catalog.yml).

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

A group with "layout: stacked" puts the note of an entry under its title
(long titles: talks, theses). A group may also hold tiles (experiments, gallery topics: a tile with
"gallery: <section id>" takes its title, counts and picture from
animations.catalog.json) and an install command (a package on PyPI).

The pages are reproducible outputs: edit a catalog, then run

  python scripts/build_outreach_pages.py           # write the pages
  python scripts/build_outreach_pages.py --check   # exit 1 if a page is stale
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LANGS = ("ru", "en")
# catalog file -> {catalog key: page}
PAGES = {
    "outreach.catalog.yml": {"outreach": "outreach.qmd", "cinema": "cinema.qmd", "interviews": "interviews.qmd"},
    "research.catalog.yml": {"research": "research.qmd"},
    "modeling.catalog.yml": {"modeling": "modeling.qmd"},
    "school.catalog.yml": {"school": "school.qmd"},
    "photos.catalog.yml": {"photos": "photos.qmd"},
    "interactives.catalog.yml": {"interactives": "interactives.qmd"},
}
GALLERY = ROOT / "animations.catalog.json"

T = {
    "ru": {
        "kinds": {"slides": "Слайды", "pdf": "PDF", "video": "Видео", "applet": "Апплет",
                  "game": "Игра", "text": "Читать", "audio": "Аудио", "pypi": "PyPI",
                  "docs": "Документация", "code": "Код", "site": "Сайт", "page": "Страница"},
        "lang_mark": {"en": "англ."},
        "formats": "Форматы",
        "install": "Установка",
        "count": lambda stories, videos: (plural_ru(stories, "сюжет", "сюжета", "сюжетов") + " · "
                                          + plural_ru(videos, "ролик", "ролика", "роликов")),
        "album": lambda photos, videos: (plural_ru(photos, "фото", "фото", "фото")
                                         + (" · " + plural_ru(videos, "видео", "видео", "видео") if videos else "")),
        "interactives": lambda n: plural_ru(n, "интерактив", "интерактива", "интерактивов"),
        "all": "Все",
        "filter": "Показать",
    },
    "en": {
        "kinds": {"slides": "Slides", "pdf": "PDF", "video": "Video", "applet": "Applet",
                  "game": "Game", "text": "Read", "audio": "Audio", "pypi": "PyPI",
                  "docs": "Documentation", "code": "Code", "site": "Website", "page": "Page"},
        "lang_mark": {"en": "EN"},
        "formats": "Formats",
        "install": "Install",
        "count": lambda stories, videos: f"{stories} stories · {videos} videos",
        "album": lambda photos, videos: f"{photos} photos" + (f" · {videos} videos" if videos else ""),
        "interactives": lambda n: f"{n} interactives",
        "all": "All",
        "filter": "Show",
    },
}


def plural_ru(number: int, one: str, few: str, many: str) -> str:
    mod10, mod100 = number % 10, number % 100
    word = one if mod10 == 1 and mod100 != 11 else few if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14 else many
    return f"{number} {word}"


def e(text: str) -> str:
    return html.escape(str(text), quote=True)


def tr(value, lang: str):
    """A text that is either one string or a {ru, en} pair."""
    if isinstance(value, dict):
        return value[lang] if lang in value else value.get("ru") or value.get("en") or ""
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
    if not entry.get("links"):
        return f'<span class="{cls}">{e(tr(entry["title"], lang))}</span>'
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
    if entry.get("install"):                     # a package: its install command under the note
        meta += f'<code class="outreach-entry-install">{e(entry["install"])}</code>'
    anchor = f' id="{e(entry["id"])}"' if entry.get("id") else ""
    links = formats(entry["links"], lang, T[lang]["formats"]) if entry.get("links") else ""
    return (f'<li class="outreach-entry"{anchor}><span class="outreach-entry-main">{title}{meta}</span>'
            f'{links}</li>')


def student_line(entry: dict, lang: str, categories: dict) -> str:
    """A supervised work: the name opens the PDF; the year and the kind of work, then its title.
    The title may hold inline HTML (sub, sup, a link to a package): it comes from the catalog."""
    links = [{"kind": "pdf", "href": entry["pdf"]}] if entry.get("pdf") else []
    name = title_link(dict(title=entry["name"], links=links), lang, "outreach-entry-title")
    kind = tr(categories[entry["category"]], lang)
    return (f'<li class="outreach-entry" data-category="{e(entry["category"])}">'
            f'<span class="outreach-entry-main">{name}'
            f'<span class="outreach-entry-note">{e(entry["year"])} · {e(kind)}</span>'
            f'<span class="outreach-entry-work">{tr(entry["work"], lang)}</span></span>'
            f'{formats(links, lang, T[lang]["formats"]) if links else ""}</li>')


FILTER_JS = """<script>
document.addEventListener('click', function (event) {
  var button = event.target.closest('.outreach-filter button');
  if (!button) return;
  var group = button.closest('.outreach-group');
  var category = button.dataset.category;
  group.querySelectorAll('.outreach-filter button').forEach(function (b) {
    b.setAttribute('aria-pressed', b === button ? 'true' : 'false');
  });
  group.querySelectorAll('.outreach-entries > li').forEach(function (row) {
    row.hidden = category !== 'all' && row.dataset.category !== category;
  });
});
</script>"""


def students_block(group: dict, lang: str) -> list[str]:
    """Counters by kind of work that filter the list, then one line per work, the newest first."""
    categories = {c["id"]: c["label"] for c in group["categories"]}
    plural = {c["id"]: c.get("plural", c["label"]) for c in group["categories"]}
    items = sorted(group["items"], key=lambda it: -int(it["year"]))
    counts = {cid: sum(it["category"] == cid for it in items) for cid in categories}
    buttons = [f'<button type="button" data-category="all" aria-pressed="true">'
               f'<strong>{len(items)}</strong> {e(T[lang]["all"].lower())}</button>']
    def word(cid: str, n: int) -> str:              # "4 кандидатские", "13 дипломных"; English: one form
        forms = tr(plural[cid], lang) if isinstance(plural[cid], dict) else plural[cid]
        return plural_ru(n, *forms).split(" ", 1)[1] if isinstance(forms, list) else forms

    buttons += [f'<button type="button" data-category="{e(cid)}" aria-pressed="false">'
                f'<strong>{n}</strong> {e(word(cid, n))}</button>'
                for cid, n in counts.items() if n]
    return ([f'      <div class="outreach-filter" role="group" aria-label="{e(T[lang]["filter"])}">'
             + "".join(buttons) + "</div>",
             '      <ul class="outreach-entries is-stacked is-students">']
            + ["        " + student_line(it, lang, categories) for it in items]
            + ["      </ul>"])


def album_tile(tile: dict, lang: str) -> dict:
    """A tile that opens a photo album; its picture and counts come from albums/<slug>/album.json."""
    album = json.loads((ROOT / "albums" / tile["album"] / "album.json").read_text(encoding="utf-8"))
    media = album["photos"]
    cover = next((m for m in media if m.get("role") == "cover"), media[0])
    picture = cover.get("preview") or cover["file"]
    photos = sum(m.get("type", "photo") == "photo" for m in media)
    return {
        "status": T[lang]["album"](photos, len(media) - photos),
        "title": tile["title"], "text": tile.get("text", ""),
        "href": f"/albums/{tile['album']}/index.html",
        "cover": f"/albums/{tile['album']}/{picture}",
    }


def gallery_tile(tile: dict, lang: str) -> dict:
    """A tile that opens one section of the animation gallery ("all": the whole gallery)."""
    catalog = json.loads(GALLERY.read_text(encoding="utf-8"))
    if tile["gallery"] == "all":
        items = [it for s in catalog["sections"] for it in s["items"]]
        section_id, item_id, video_id = tile["cover"].split("/")
        return {
            "status": T[lang]["count"](len(items), sum(len(it["videos"]) for it in items)),
            "title": tile["title"], "text": tile["text"], "href": f"/{lang}/animations.html",
            "cover": f"/assets/animations/dvnanima/{section_id}-{item_id}-{video_id}.jpg",
        }
    sections = {s["id"]: s for s in catalog["sections"]}
    section = sections[tile["gallery"]]
    item_id, video_id = tile["cover"].split("/") if tile.get("cover") else (
        section["items"][0]["id"], section["items"][0]["videos"][0]["id"])
    poster = f"/assets/animations/dvnanima/{section['id']}-{item_id}-{video_id}.jpg"
    videos = sum(len(it["videos"]) for it in section["items"])
    return {
        "status": T[lang]["count"](len(section["items"]), videos),
        "title": section.get(f"title_{lang}") or section["title"],
        "text": section.get(f"summary_{lang}") or section["summary"],
        "href": f"/{lang}/animations.html#{section['id']}",
        "cover": poster if (ROOT / poster.lstrip("/")).exists() else "",
    }


def tiles_block(tiles: list[dict], lang: str, label: str) -> list[str]:
    albums = " is-albums" if any(tile.get("album") for tile in tiles) else ""
    out = [f'      <nav class="course-tiles outreach-tiles{albums}" aria-label="{e(label)}">']
    for tile in tiles:
        if tile.get("gallery"):
            tile = gallery_tile(tile, lang)
        elif tile.get("album"):
            tile = album_tile(tile, lang)
        elif tile.get("count_of"):           # a tile for a catalog page: the number of its entries
            catalog = yaml.safe_load((ROOT / tile["count_of"]).read_text(encoding="utf-8"))
            section = next(iter(catalog.values()))
            n = sum(len(g.get("items", [])) for g in section["groups"])
            tile = dict(tile, status=T[lang]["interactives"](n))
        url = href(tile, lang)
        picture = tile.get("cover", "")
        if picture.startswith("/") and not (ROOT / picture.lstrip("/")).exists():
            sys.exit(f"missing tile picture: {picture}")
        cover = (f'<img class="course-tile-cover" src="{e(href(tile, lang, "cover"))}" alt="" loading="lazy">'
                 if picture else "")
        out.append(f'        <div class="course-tile{" has-cover" if cover else ""}">{cover}'
                   f'<span class="course-tile-status is-ready">{e(tr(tile["status"], lang))}</span>'
                   f'<a class="course-tile-title" href="{e(url)}"{external(url)}>{e(tr(tile["title"], lang))}</a>'
                   + (f'<span class="course-tile-text">{e(tr(tile["text"], lang))}</span>' if tile.get("text") else "")
                   + '</div>')
    out.append("      </nav>")
    return out


def install_block(group: dict, lang: str) -> list[str]:
    note = tr(group.get("install_note"), lang)
    return ['      <div class="outreach-install">',
            f'        <span class="outreach-install-label">{e(T[lang]["install"])}</span>',
            f'        <code>{e(group["install"])}</code>',
            *([f'        <span class="outreach-install-note">{e(note)}</span>'] if note else []),
            "      </div>"]


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
        if tr(group.get("summary"), lang):
            out.append(f'        <p class="outreach-group-text">{e(tr(group["summary"], lang))}</p>')
        if group.get("links"):
            out.append("        " + formats(group["links"], lang, T[lang]["formats"]))
        out.append("      </div>")
    if group.get("install"):
        out += install_block(group, lang)
    if group.get("tiles"):
        out += tiles_block(group["tiles"], lang, tr(group.get("title"), lang))
    if group.get("categories"):
        out += students_block(group, lang)
        out.append("    </div>")
        return out
    entries = entries_of(group, lang)
    if entries:
        stacked = " is-stacked" if group.get("layout") == "stacked" else ""
        out.append(f'      <ul class="outreach-entries{stacked}">')
        out += ["        " + entry_line(entry, lang) for entry in entries]
        out.append("      </ul>")
    if group.get("all"):
        url = href(group["all"], lang)
        out.append(f'      <a class="outreach-all" href="{e(url)}">{e(tr(group["all"]["label"], lang))} →</a>')
    out.append("    </div>")
    return out


def page(section: dict, lang: str, variant: str = "") -> str:
    out = ["---", f'title: "{tr(section["title"], lang)}"']
    if section.get("aliases"):                  # old addresses of the page
        out += ["aliases:"] + [f"  - {alias}" for alias in section["aliases"]]
    if lang == "en":
        out.append("lang: en-US")
    out += ["toc: false", "---", "", "```{=html}", '<div class="lecture-catalog outreach-catalog">',
            f'  <p class="lecture-catalog-lead">{e(tr(section["lead"], lang))}</p>']
    if section.get("topics"):                   # buttons to the groups, with the number of entries
        out.append(f'  <nav class="anim-topics" aria-label="{e(tr(section["title"], lang))}">')
        out += [f'    <a href="#{e(g["id"])}">{e(tr(g["title"], lang))}<span>{len(g.get("items", []))}</span></a>'
                for g in section["groups"]]
        out.append("  </nav>")
    out.append(f'  <div class="outreach-list{variant}">')
    for group in section["groups"]:
        out += group_block(group, lang)
    out.append("  </div>")
    if any(group.get("categories") for group in section["groups"]):
        out.append(FILTER_JS)
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


def outputs(langs=LANGS) -> dict[Path, str]:
    pages = {}
    for file, names in PAGES.items():
        catalog = yaml.safe_load((ROOT / file).read_text(encoding="utf-8"))
        if catalog.get("interviews", {}).get("pages"):
            catalog["interviews"] = pages_as_entries(catalog["interviews"])
        pages.update({ROOT / lang / name: page(catalog[key], lang)
                      for lang in langs for key, name in names.items() if catalog.get(key, {}).get("groups")})
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale pages, write nothing")
    parser.add_argument("--lang", choices=LANGS, help="only the pages of this language")
    args = parser.parse_args()

    stale = []
    for path, text in outputs((args.lang,) if args.lang else LANGS).items():
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
