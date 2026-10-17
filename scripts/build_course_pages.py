#!/usr/bin/env python3
"""Write the education pages and the course pages of the site from courses.catalog.yml.

The catalog lists the sections of the education page and every lecture course.
Each course becomes ru/courses/<slug>.qmd and en/courses/<slug>.qmd: a header
with the course links, a table of contents (number, topic, slides, PDF, video,
problems, book chapter, further materials; only the columns the course has),
the book with its chapters, further materials and related courses.
ru/education.qmd and en/education.qmd get one tile per course, grouped by
section; each tile keeps the anchor the old page had, so existing links and
slide footers still land on it.

The pages are reproducible outputs: edit the catalog, then run

  python scripts/build_course_pages.py          # write the pages
  python scripts/build_course_pages.py --check  # exit 1 if a page is stale
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "courses.catalog.yml"
LANGS = ("ru", "en")

T = {
    "ru": {
        "home": "NeutrinoHit", "education": "Образование", "all": "← Все курсы",
        "num": "№", "topic": "Тема", "slides": "Слайды", "pdf": "PDF", "video": "Видео",
        "exercises": "Задачи", "chapter": "Глава", "extra": "Ещё",
        "open": "открыть", "contents": "Оглавление", "book": "Книга", "open_book": "Открыть книгу",
        "chapters": "Главы", "materials": "Материалы", "related": "Ещё в этом разделе",
        "reading": "Рекомендуемая литература",
        "lectures": lambda n: f"{n} {plural(n, 'лекция', 'лекции', 'лекций')}",
        "videos": lambda n: f"{n} видео",
        "hours": lambda h, m: f"{h} ч {m:02d} мин видео",
        "hours_short": lambda h: f"{h} ч",
        "in_lang": {"en": "лекции на английском", "ru": None},
        "extra_of": lambda n: f"К лекции {n}",
        "aria_video": lambda n: f"Видео лекции {n}",
        "book_short": "онлайн‑книга",
        "programs": "Программы",
    },
    "en": {
        "home": "NeutrinoHit", "education": "Education", "all": "← All courses",
        "num": "No.", "topic": "Topic", "slides": "Slides", "pdf": "PDF", "video": "Video",
        "exercises": "Problems", "chapter": "Chapter", "extra": "More",
        "open": "open", "contents": "Contents", "book": "Book", "open_book": "Open the book",
        "chapters": "Chapters", "materials": "Materials", "related": "More in this section",
        "reading": "Recommended reading",
        "lectures": lambda n: f"{n} lecture{'s' if n != 1 else ''}",
        "videos": lambda n: f"{n} video{'s' if n != 1 else ''}",
        "hours": lambda h, m: f"{h} h {m:02d} min of video",
        "hours_short": lambda h: f"{h} h",
        "in_lang": {"ru": "lectures in Russian", "en": None},
        "extra_of": lambda n: f"For lecture {n}",
        "aria_video": lambda n: f"Video of lecture {n}",
        "book_short": "online book",
        "programs": "Programs",
    },
}
COLUMNS = ("slides", "pdf", "video", "exercises", "chapter", "extra")


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many


def e(text: str) -> str:
    return html.escape(str(text), quote=True)


def tr(value, lang: str) -> str:
    """A text that is either one string or a {ru, en} pair."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("ru") or value.get("en") or ""
    return value or ""


def href(item: dict, lang: str, key: str = "href", depth: int = 2) -> str:
    """A link from a page <depth> folders below the site root; site paths start with '/'."""
    path = item.get(f"{key}_en") if lang == "en" and item.get(f"{key}_en") else item[key]
    return "/".join([".."] * depth) + path if path.startswith("/") else path


def hms(seconds: int) -> str:
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def lectures_of(course: dict, lang: str) -> list[dict]:
    if lang == "en" and "lectures_en" in course:
        return course["lectures_en"] or []
    return course.get("lectures") or []


def video_url(lecture: dict, course: dict) -> str:
    url = f"https://www.youtube.com/watch?v={lecture['video']}"
    if course.get("playlist"):
        url += f"&amp;list={course['playlist']}"
    return url


def cell(lecture: dict, column: str, course: dict, lang: str) -> str:
    t = T[lang]
    if column == "video":
        if not lecture.get("video"):
            return ""
        time = hms(lecture["seconds"]) if lecture.get("seconds") else ""
        return (f'<a class="course-play" href="{video_url(lecture, course)}" '
                f'aria-label="{e(t["aria_video"](lecture["n"]))}">▶ {time}</a>')
    if column == "extra":
        extra = lecture.get("extra") or []
        return f'<a href="#lecture-{e(lecture["n"])}-more">{t["extra"].lower()}&nbsp;{len(extra)}</a>' if extra else ""
    if not lecture.get(column):
        return ""
    label = t[column] if column == "pdf" else t[column].lower()
    return f'<a href="{e(href(lecture, lang, column))}">{label}</a>'


def course_counts(course: dict, lang: str) -> tuple[int, int, int]:
    lectures = lectures_of(course, lang)
    videos = sum(1 for l in lectures if l.get("video"))
    seconds = sum(l.get("seconds", 0) for l in lectures)
    return len(lectures), videos, seconds


def page(course: dict, catalog: dict, lang: str) -> str:
    t = T[lang]
    title = tr(course["title"], lang)
    lectures = lectures_of(course, lang)
    columns = [c for c in COLUMNS if any(l.get(c) for l in lectures)]
    n, videos, seconds = course_counts(course, lang)

    meta = []
    if n:
        meta.append(t["lectures"](n))
    if seconds:
        h, m = divmod(round(seconds / 60), 60)
        meta.append(t["hours"](h, m))
    note = t["in_lang"].get(course.get("materials_lang_en" if lang == "en" else "materials_lang", lang))
    if note:
        meta.append(note)

    out = [
        "---",
        f'pagetitle: "{title} – NeutrinoHit"',
        f"lang: {'ru-RU' if lang == 'ru' else 'en-US'}",
        "toc: false",
        "---",
        "",
        "```{=html}",
        f'<article class="course-page" data-course="{e(course["slug"])}">',
        f'  <nav class="course-crumbs" aria-label="breadcrumbs"><a href="../index.html">{t["home"]}</a><span>›</span>'
        f'<a href="../education.html">{t["education"]}</a><span>›</span><span>{e(title)}</span></nav>',
        '  <header class="course-page-head">',
        f'    <span class="course-tile-status{" is-ready" if course.get("ready", True) else ""}">{e(tr(course["kind"], lang))}</span>',
        f"    <h1>{e(title)}</h1>",
        f'    <p class="course-page-summary">{e(tr(course["summary"], lang))}</p>',
    ]
    if meta:
        out.append(f'    <p class="course-toc-meta">{" · ".join(e(m) for m in meta)}</p>')
    links = (course.get("links_en") if lang == "en" and "links_en" in course else course.get("links")) or []
    if links:
        out.append('    <div class="lecture-course-actions">')
        for link in links:
            cls = ' class="lecture-action-primary"' if link.get("primary") else ""
            out.append(f'      <a{cls} href="{e(href(link, lang))}">{e(tr(link["label"], lang))}</a>')
        out.append("    </div>")
    out.append("  </header>")

    if course.get("status_note"):
        out.append(f'  <p class="course-page-note">{e(tr(course["status_note"], lang))}</p>')

    if lectures:
        out += [
            f'  <h2 class="course-page-section">{t["contents"]}</h2>',
            '  <table class="course-toc course-toc-full">',
            '    <thead><tr><th class="course-toc-num">' + t["num"] + "</th><th>" + t["topic"] + "</th>"
            + "".join(f'<th class="course-toc-col">{t[c]}</th>' for c in columns) + "</tr></thead>",
            "    <tbody>",
        ]
        for lecture in lectures:
            topic = e(tr(lecture["title"], lang))
            if lecture.get("slides"):
                topic = f'<a href="{e(href(lecture, lang, "slides"))}">{topic}</a>'
            elif lecture.get("video"):
                topic = f'<a href="{video_url(lecture, course)}">{topic}</a>'
            if lecture.get("note"):
                topic += f' <span class="course-toc-note">{e(tr(lecture["note"], lang))}</span>'
            cells = "".join(
                f'<td class="course-toc-col" data-label="{t[c]}">{cell(lecture, c, course, lang)}</td>' for c in columns
            )
            out.append(
                f'      <tr id="lecture-{e(lecture["n"])}"><td class="course-toc-num">{e(lecture["n"])}</td>'
                f'<td class="course-toc-topic">{topic}</td>{cells}</tr>'
            )
        out += ["    </tbody>", "  </table>"]

    book = course.get("book")
    if book:
        out += [
            f'  <h2 class="course-page-section">{t["book"]}</h2>',
            '  <div class="course-page-card">',
            f'    <p><strong>{e(tr(book["title"], lang))}</strong>. {e(tr(book["note"], lang))}</p>',
            f'    <div class="lecture-course-actions"><a class="lecture-action-primary" href="{e(href(book, lang))}">{t["open_book"]}</a></div>',
        ]
        chapters = book.get("chapters_en") if lang == "en" and "chapters_en" in book else book.get("chapters")
        if chapters:
            out.append(f'    <h3>{t["chapters"]}</h3>')
            out.append('    <ol class="course-book-chapters">')
            for chapter in chapters:
                out.append(f'      <li><a href="{e(href(chapter, lang))}">{e(tr(chapter["title"], lang))}</a></li>')
            out.append("    </ol>")
        out.append("  </div>")

    if course.get("reading"):
        reading = (ROOT / "_includes" / f"{course['reading']}-{lang}.html").read_text(encoding="utf-8").strip()
        out += [f'  <h2 class="course-page-section">{t["reading"]}</h2>',
                '  <div class="course-page-card course-page-reading">', reading, "  </div>"]

    groups = list((course.get("materials_en") if lang == "en" and "materials_en" in course else course.get("materials")) or [])
    for lecture in lectures:
        if lecture.get("extra"):
            label = t["extra_of"](lecture["n"])
            if course.get("extra_title"):
                label = f'{tr(course["extra_title"], lang)} · {label[0].lower()}{label[1:]}'
            groups.append({"id": f"lecture-{lecture['n']}-more", "title": label, "items": lecture["extra"]})
    if groups:
        out.append(f'  <h2 class="course-page-section">{t["materials"]}</h2>')
        for group in groups:
            gid = f' id="{e(group["id"])}"' if group.get("id") else ""
            out.append(f'  <div class="course-page-card"{gid}>')
            out.append(f'    <h3>{e(tr(group["title"], lang))}</h3>')
            if group.get("text"):
                out.append(f'    <p>{e(tr(group["text"], lang))}</p>')
            out.append('    <div class="lecture-course-actions">')
            for item in group["items"]:
                out.append(f'      <a href="{e(href(item, lang))}">{e(tr(item["label"], lang))}</a>')
            out += ["    </div>", "  </div>"]

    related = [c for c in catalog["courses"] if c["slug"] in (course.get("related") or [])]
    if related:
        out.append(f'  <h2 class="course-page-section">{t["related"]}</h2>')
        out.append('  <nav class="course-tiles">')
        for other in related:
            out.append(tile(other, lang, page_depth=2, with_anchor=False))
        out.append("  </nav>")

    out += [f'  <p class="course-page-back"><a href="../education.html">{t["all"]}</a></p>', "</article>", "```", ""]
    return "\n".join(out)


def tile(course: dict, lang: str, page_depth: int, with_anchor: bool = True) -> str:
    """A tile; page_depth is 1 on <lang>/education.html and 2 on a course page."""
    t = T[lang]
    n, videos, seconds = course_counts(course, lang)
    meta = []
    if videos:
        meta.append(e(t["videos"](videos)))
        if seconds:
            meta.append(e(t["hours_short"](round(seconds / 3600))))
    elif n:
        meta.append(e(t["lectures"](n)))
    for item in course.get("tile_meta") or []:
        if isinstance(item, dict) and item.get("href"):
            meta.append(f'<a class="course-tile-book" href="{e(href(item, lang, depth=page_depth))}">{e(tr(item["label"], lang))}</a>')
        else:
            meta.append(e(tr(item, lang)))
    book = course.get("book")
    if book and not course.get("tile_no_book"):
        meta.append(f'<a class="course-tile-book" href="{e(href(book, lang, depth=page_depth))}">{t["book_short"]}</a>')
    target = f"courses/{course['slug']}.html" if page_depth == 1 else f"{course['slug']}.html"
    anchor = f' id="{e(course["anchor"])}"' if with_anchor and course.get("anchor") else ""
    ready = " is-ready" if course.get("ready", True) else ""
    text = tr(course.get("tile") or course["summary"], lang)
    meta_html = f'<span class="course-tile-meta">{" · ".join(meta)}</span>' if meta else ""
    return (f'    <div class="course-tile"{anchor}><span class="course-tile-status{ready}">{e(tr(course["kind"], lang))}</span>'
            f'<a class="course-tile-title" href="{target}">{e(tr(course["title"], lang))}</a>'
            f'<span class="course-tile-text">{e(text)}</span>{meta_html}</div>')


def education(catalog: dict, lang: str) -> str:
    edu = catalog["education"]
    by_slug = {c["slug"]: c for c in catalog["courses"]}
    out = [
        "---",
        f'title: "{tr(edu["title"], lang)}"',
    ]
    if lang == "en":
        out.append("lang: en-US")
    out += ["toc: false", "---", "", "```{=html}", '<div class="lecture-catalog">',
            f'  <p class="lecture-catalog-lead">{e(tr(edu["lead"], lang))}</p>', ""]
    for section in edu["sections"]:
        out.append(f'  <h2 id="{e(section["id"])}" class="section-inline-title">{e(tr(section["title"], lang))}</h2>')
        if section.get("line"):
            line = section["line"]
            out.append(f'  <p class="course-book-line">{e(tr(line["text"], lang))} '
                       f'<a href="{e(href(line, lang, depth=1))}">{e(tr(line["label"], lang))}</a></p>')
        out.append(f'  <nav class="course-tiles" aria-label="{e(tr(section["title"], lang))}">')
        for slug in section["courses"]:
            out.append(tile(by_slug[slug], lang, page_depth=1))
        out += ["  </nav>", ""]
    program = (ROOT / "_includes" / f"education-program-{lang}.html").read_text(encoding="utf-8").strip()
    out += [f'  <h2 id="programs" class="section-inline-title">{T[lang]["programs"]}</h2>',
            "  " + program.replace("\n", "\n  "), "</div>", "```", ""]
    return "\n".join(out)


def outputs(catalog: dict) -> dict[Path, str]:
    files = {}
    for lang in LANGS:
        files[ROOT / lang / "education.qmd"] = education(catalog, lang)
        for course in catalog["courses"]:
            files[ROOT / lang / "courses" / f"{course['slug']}.qmd"] = page(course, catalog, lang)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report stale pages, write nothing")
    args = parser.parse_args()

    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    stale = []
    for path, text in outputs(catalog).items():
        if path.exists() and path.read_text(encoding="utf-8") == text:
            continue
        stale.append(path.relative_to(ROOT))
        if not args.check:
            path.parent.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
    for path in stale:
        print(("stale  " if args.check else "wrote  ") + str(path))
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
