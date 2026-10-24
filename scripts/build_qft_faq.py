#!/usr/bin/env python3
"""Build the page of frequently asked questions on QFT from the LaTeX source of the book.

Source of truth: the book repository TheBook (a sibling folder, or --thebook):
  chapters/FAQ.tex (Russian) and en/chapters/FAQ.tex (English): the abstract is the lead of the page,
  every \\section is a question; a section without text is shown as a question whose answer is in preparation.
A question that the site answers with a lecture rather than with a text of the book is listed in EXTRA.

Outputs (committed; make site does not run this script, it needs the book sources):
  ru|en/qft-faq.qmd    one page: the list of questions, then the answers (MathJax formulas, references)

Usage:
  python scripts/build_qft_faq.py           # write the pages
  python scripts/build_qft_faq.py --check   # the pages are up to date with the sources
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_qft_exams import braced, e, format_ref, html_inline, parse_bib, plain, strip_comments, to_markdown  # noqa: E402

SITE_ROOT = Path(__file__).resolve().parents[1]
LANGS = ("ru", "en")

# anchors of the questions, in the order of \section in FAQ.tex (both languages)
SLUGS = [
    "field-or-particle", "pointlike-particle", "boiling-vacuum", "virtual-particle",
    "feynman-diagrams", "virtual-to-real", "casimir-effect", "wave-function-collapse",
]
# questions answered on the site by a lecture; they follow the questions of the book
EXTRA = [
    {
        "slug": "attraction",
        "title": {"ru": "Как увидеть в КТП, что частицы притягиваются?",
                  "en": "How can one see in QFT that particles attract?"},
        "body": {"ru": "Этому посвящена отдельная лекция "
                       "[«Притяжение и отталкивание в КТП»](courses/qft-attraction-repulsion.html) (на английском): "
                       "скалярная КЭД и волновые пакеты.",
                 "en": "This is the subject of a separate lecture, "
                       "[Attraction and Repulsion in QFT](courses/qft-attraction-repulsion.html): "
                       "scalar QED and wave packets."},
    },
]

T = {
    "ru": {
        "lang": "ru-RU", "site": "NeutrinoHit", "education": "Образование",
        "title": "Часто задаваемые вопросы по квантовой теории поля",
        "short": "ЧАВО по КТП",
        "kind": "ЧАВО по КТП",
        "questions": lambda n: f"{n} {plural_ru(n, 'вопрос', 'вопроса', 'вопросов')} · ответы пополняются",
        "num": "№", "question": "Вопрос", "status": "Ответ",
        "state": {"ready": "есть", "pending": "готовится", "lecture": "лекция"},
        "pending": "Ответ готовится.",
        "contents": "← К списку вопросов",
        "refs": "Литература",
        # the abstract of the chapter speaks of "this chapter"; on the site it is this page
        "here": ("В этой главе", "Здесь"),
        "updated": "Вопросы и ответы пополняются — заглядывайте сюда регулярно.",
        "book_line": "Книга:",
        "book_label": "«Квантовая теория поля для экспериментаторов и не только» →",
        "book_href": "materials.html#qft-book",
        "description": "Концептуальные вопросы квантовой теории поля: поле или частица, точечна ли частица, "
                       "кипит ли вакуум, что такое виртуальная частица. Ответы Д. В. Наумова.",
    },
    "en": {
        "lang": "en-US", "site": "NeutrinoHit", "education": "Education",
        "title": "Frequently asked questions on quantum field theory",
        "short": "QFT FAQ",
        "kind": "QFT FAQ",
        "questions": lambda n: f"{n} question{'s' if n != 1 else ''} · answers are being added",
        "num": "No.", "question": "Question", "status": "Answer",
        "state": {"ready": "ready", "pending": "in preparation", "lecture": "lecture"},
        "pending": "The answer is in preparation.",
        "contents": "← Back to the questions",
        "refs": "References",
        "here": ("In this chapter", "Here"),
        "updated": "Questions and answers are being added, so check back regularly.",
        "book_line": "Book:",
        "book_label": "“Quantum Field Theory for Experimentalists and Beyond” →",
        "book_href": "materials.html#qft-book",
        "description": "Conceptual questions of quantum field theory: field or particle, is a particle pointlike, "
                       "does the vacuum boil, what is a virtual particle. Answers by D. V. Naumov.",
    },
}


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


# ------------------------------------------------------------------ sources

def load_faq(book: Path, lang: str) -> tuple[list[str], list[dict]]:
    """The paragraphs of the abstract and the questions of FAQ.tex."""
    base = book if lang == "ru" else book / "en"
    tex = strip_comments((base / "chapters" / "FAQ.tex").read_text(encoding="utf-8"))
    tex = tex[tex.index("\\begin{mychapter}"):tex.index("\\end{mychapter}")]
    m = re.search(r"\\ChapterAbstract\s*(?=\{)", tex)
    abstract, end = braced(tex, m.end())
    parts = [p for p in re.split(r"(?=\\section\{)", tex[end:]) if p.strip().startswith("\\section{")]
    if len(parts) != len(SLUGS):
        raise SystemExit(f"{lang}: {len(parts)} questions in FAQ.tex, {len(SLUGS)} anchors in SLUGS")
    questions = []
    for slug, part in zip(SLUGS, parts):
        title, end = braced(part, len("\\section"))
        body = re.sub(r"\\index\{[^{}]*\}", "", part[end:]).strip()
        questions.append({"slug": slug, "title": title.strip(), "body": body})
    paragraphs = [inline_html(p, lang) for p in re.split(r"\n\s*\n", abstract) if p.strip()]
    return paragraphs, questions


def inline_html(text: str, lang: str) -> str:
    """A paragraph of plain text of the book (no formulas) in HTML."""
    text = re.sub(r"\s+", " ", text).strip()
    if lang == "ru":
        text = text.replace("<<", "«").replace(">>", "»")
    else:
        text = text.replace("``", "“").replace("''", "”")
    text = text.replace("~---", "\u00a0—").replace("---", "—").replace("--", "–").replace("~", "\u00a0")
    return e(text)


# ------------------------------------------------------------------- pages

def page(lang: str, abstract: list[str], questions: list[dict], bib: dict) -> str:
    t = T[lang]
    items = [dict(q, state="ready" if q["body"] else "pending") for q in questions]
    items += [{"slug": x["slug"], "title": x["title"][lang], "body": x["body"][lang], "state": "lecture"} for x in EXTRA]
    old, new = t["here"]
    lead = [p.replace(old, new, 1) for p in abstract]
    out = [
        "---",
        f'pagetitle: "{t["title"]}"',
        f"lang: {t['lang']}",
        f'description: "{t["description"]}"',
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="course-page qft-faq">',
        f'  <nav class="course-crumbs" aria-label="breadcrumbs"><a href="index.html">{t["site"]}</a><span>›</span>'
        f'<a href="education.html">{t["education"]}</a><span>›</span><span>{t["short"]}</span></nav>',
        '  <header class="course-page-head">',
        f'    <span class="course-tile-status is-ready">{t["kind"]}</span>',
        f'    <h1>{t["title"]}</h1>',
        *[f'    <p class="course-page-summary">{p}</p>' for p in lead],
        f'    <p class="course-toc-meta">{e(t["questions"](len(items)))}</p>',
        "  </header>",
        '  <table id="questions" class="course-toc course-toc-full qft-faq-toc">',
        f'    <thead><tr><th class="course-toc-num">{t["num"]}</th><th>{t["question"]}</th>'
        f'<th class="qft-faq-state">{t["status"]}</th></tr></thead>',
        "    <tbody>",
    ]
    for i, item in enumerate(items, 1):
        out.append(f'      <tr><td class="course-toc-num">{i:02d}</td>'
                   f'<td class="course-toc-topic"><a href="#{item["slug"]}">{html_inline(item["title"])}</a></td>'
                   f'<td class="qft-faq-state is-{item["state"]}">{t["state"][item["state"]]}</td></tr>')
    out += ["    </tbody>", "  </table>", "```", "", "::: {.qft-exam-body .qft-faq-body}"]
    refs: list[str] = []
    for i, item in enumerate(items, 1):
        out += [f"## {i}. {plain(item['title'])} {{#{item['slug']}}}", ""]
        if item["state"] == "ready":
            # \subsection* of a question is a heading one level below the question
            body = re.sub(r"\\subsection\*?\s*(?=\{)", r"\\subsubsection*", item["body"])
            out.append(to_markdown(body, lang, refs).rstrip())
        elif item["state"] == "lecture":
            out.append(item["body"])
        else:
            out += ["::: {.qft-faq-pending}", t["pending"], ":::"]
        out += ["", f"[{t['contents']}](#questions){{.qft-faq-up}}", ""]
    if refs:
        out += [f"## {t['refs']}", ""]
        for i, key in enumerate(refs, 1):
            if key not in bib:
                raise SystemExit(f"{lang}: unknown reference {key}")
            out.append(f"[{i}]{{#ref-{i}}} {format_ref(bib[key])}" + "\\")
        out[-1] = out[-1].rstrip("\\")
        out.append("")
    out += [":::", "", "```{=html}",
            f'  <p class="course-page-note">{e(t["updated"])}</p>',
            f'  <p class="course-book-line">{e(t["book_line"])} <a href="{t["book_href"]}">{e(t["book_label"])}</a></p>',
            f'  <p class="course-page-back"><a href="education.html">← {t["education"]}</a></p>',
            "</article>", "```", ""]
    return "\n".join(out)


# -------------------------------------------------------------------- main

def outputs(book: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for lang in LANGS:
        abstract, questions = load_faq(book, lang)
        bib = parse_bib(book / ("references.bib" if lang == "ru" else "en/references.bib"))
        files[SITE_ROOT / lang / "qft-faq.qmd"] = page(lang, abstract, questions, bib)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--thebook", type=Path, default=SITE_ROOT.parent / "TheBook")
    parser.add_argument("--check", action="store_true", help="only check that the pages are up to date")
    args = parser.parse_args()
    files = outputs(args.thebook)
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(SITE_ROOT)}")
        return 1 if stale else 0
    for p in stale:
        p.write_text(files[p], encoding="utf-8")
        print(f"wrote {p.relative_to(SITE_ROOT)}")
    print(f"{len(files)} pages, {len(stale)} changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
