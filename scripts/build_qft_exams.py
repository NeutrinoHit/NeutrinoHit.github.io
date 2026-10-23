#!/usr/bin/env python3
"""Build the pages of the examination projects of the QFT course from the LaTeX sources of the book.

Source of truth: the book repository TheBook (a sibling folder, or --thebook):
  autumn  chapters/Exams1.tex (topics, order) + projects/<Name>.tex (one project per file)
  spring  chapters/Exams2.tex (one \\section per project)
and their English versions en/chapters/Exams1.tex, en/projects/<Name>.tex, en/chapters/Exams2.tex.

Outputs (committed; make site does not run this script, it needs the book sources):
  ru|en/qft-exams.qmd             the list: autumn and spring, a row per project
  ru|en/qft-exams/<slug>.qmd      a page per project (MathJax formulas, references, neighbours)
  assets/qft-exams/qft-exams-<season>-<lang>.pdf   with --pdf (LuaLaTeX, every project on its own page)
The file of pseudo-data of the neutral kaon project (assets/qft-exams/kaon-asymmetry-pseudodata.txt) is a static asset.

Usage:
  python scripts/build_qft_exams.py           # write the pages
  python scripts/build_qft_exams.py --pdf     # also build the four PDFs (latexmk, lualatex)
  python scripts/build_qft_exams.py --check   # the pages are up to date with the sources
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = SITE_ROOT / "assets" / "qft-exams"
BASE_URL = "https://neutrinohit.github.io"
LANGS = ("ru", "en")
SEASONS = ("autumn", "spring")

# autumn: file of projects/ -> slug of the page; spring: slugs in the order of \section in Exams2.tex
AUTUMN_SLUGS = {
    "HarmonicOscillator": "harmonic-chain", "HydrogenAtom": "hydrogen-atom", "PiAtom": "pionium",
    "Resonances": "resonances", "KleinParadox": "klein-paradox", "Dirac_1d": "dirac-1plus1", "Tremor": "tremor",
    "DiracMatrices": "dirac-matrices", "SternGerlach": "stern-gerlach", "QuantumEraser": "quantum-eraser",
    "U1symmetry": "dirac-symmetries", "SigmaModel": "sigma-model", "ChiralAnomaly": "chiral-anomaly",
    "Casimir": "casimir", "CasimirDinamic": "dynamical-casimir", "Diffraction": "diffraction", "Tachyon": "tachyon",
    "BerryPhase": "berry-phase", "LandauLevels": "landau-levels", "AharonovBohm": "aharonov-bohm",
}
SPRING_SLUGS = [
    "varying-masses", "z-pole", "solar-neutrinos", "relic-neutrinos", "reactor-antineutrinos", "neutral-pion",
    "glashow-resonance", "neutral-kaons", "higgs-decay", "neutrino-dose", "vacuum-birefringence", "orthopositronium",
    "cherenkov", "cosmological-constant", "functional-integral", "grand-unification", "unstable-particles",
    "polarizing-glasses",
]
# extra downloads of a project page: slug -> [(file in assets/qft-exams, label)]
FILES = {
    "neutral-kaons": [("kaon-asymmetry-pseudodata.txt",
                       {"ru": "Псевдоданные: асимметрия распада (TXT)", "en": "Pseudo-data: decay asymmetry (TXT)"})],
}

T = {
    "ru": {
        "lang": "ru-RU", "site": "NeutrinoHit", "education": "Образование",
        "title": "Экзаменационные проекты по квантовой теории поля",
        "short": "Экзаменационные проекты",
        "kind": "Экзамен · проекты",
        "season": {"autumn": "Осень", "spring": "Весна"},
        "season_long": {"autumn": "Осенний семестр", "spring": "Весенний семестр"},
        "season_lead": {
            "autumn": "Квантовая механика, уравнение Дирака, симметрии и вакуум: первый семестр курса.",
            "spring": "КЭД, Стандартная модель, нейтрино и космология: второй семестр курса.",
        },
        "projects": lambda n: f"{n} {plural_ru(n, 'проект', 'проекта', 'проектов')}",
        "lead": ("Экзамен по курсу «Квантовая теория поля для экспериментаторов» проходит в виде мини-проектов. "
                 "Каждый студент получает собственную задачу и примерно неделю на подготовку. "
                 "Каждый проект — небольшая научная работа: теория, расчёт, моделирование и сравнение с экспериментом."),
        "updated": "Проекты обновляются и пополняются — заглядывайте сюда регулярно.",
        "pdf": "PDF", "pdf_season": lambda s: f"{s}: все проекты, PDF",
        "num": "№", "project": "Проект", "topic": "Тема",
        "how": "Как устроен проект",
        "goals": "Цели",
        "goals_items": [
            "Применение полученных знаний для решения реальных научных задач.",
            "Освоение научных инструментов: LaTeX, git, python.",
            "Развитие навыков совместной работы над проектами.",
            "Критическое мышление и креативность: проекты побуждают находить нестандартные решения и аргументировать их.",
        ],
        "structure": "Структура отчёта",
        "structure_items": [
            "Введение: мотивация, краткий обзор литературы, постановка задачи.",
            "Теоретическая часть: выводы, расчёты, формулы.",
            "Практическая часть: моделирование, анализ данных, расчёты.",
            "Обсуждение: графики, таблицы, интерпретация результатов.",
            "Выводы: основные результаты, предложения по продолжению работы.",
            "Список литературы: все использованные источники.",
        ],
        "tools": "Технические аспекты",
        "tools_items": [
            "Оформление проекта в LaTeX; можно использовать онлайн-сервис overleaf.com.",
            "Фейнмановские диаграммы — пакет tikz-feynman.",
            "Графики — библиотека matplotlib.",
        ],
        "book_line": "Учебник к курсу:",
        "book_label": "«Квантовая теория поля для экспериментаторов и не только» →",
        "book_href": "/ru/materials.html#qft-book",
        "of": lambda i, n: f"проект {i} из {n}",
        "prev": "Предыдущий", "next": "Следующий", "all": "← Все проекты",
        "refs": "Литература", "files": "Файлы к проекту",
        "pdf_title": "Экзаменационные проекты по квантовой теории поля",
        "author": "Д.~В.~Наумов",
        "toc": "Содержание",
        "description": "Экзаменационные проекты курса квантовой теории поля Д. В. Наумова: осень и весна, задачи с теорией, расчётом и моделированием.",
    },
    "en": {
        "lang": "en-US", "site": "NeutrinoHit", "education": "Education",
        "title": "Examination projects in quantum field theory",
        "short": "Examination projects",
        "kind": "Exam · projects",
        "season": {"autumn": "Autumn", "spring": "Spring"},
        "season_long": {"autumn": "Autumn term", "spring": "Spring term"},
        "season_lead": {
            "autumn": "Quantum mechanics, the Dirac equation, symmetries and the vacuum: the first term of the course.",
            "spring": "QED, the Standard Model, neutrinos and cosmology: the second term of the course.",
        },
        "projects": lambda n: f"{n} project{'s' if n != 1 else ''}",
        "lead": ("The examination in the course “Quantum Field Theory for Experimentalists” takes the form of mini-projects. "
                 "Each student receives an individual problem and about a week to prepare. "
                 "Each project is a small piece of research: theory, calculation, simulation and comparison with experiment."),
        "updated": "The projects are updated and expanded, so check back regularly.",
        "pdf": "PDF", "pdf_season": lambda s: f"{s}: all projects, PDF",
        "num": "No.", "project": "Project", "topic": "Topic",
        "how": "How a project is organized",
        "goals": "Goals",
        "goals_items": [
            "Applying the knowledge gained to real scientific problems.",
            "Mastering the tools of research: LaTeX, git, python.",
            "Developing the skills of working together on projects.",
            "Critical thinking and creativity: the projects encourage unconventional solutions and well-argued conclusions.",
        ],
        "structure": "Structure of the report",
        "structure_items": [
            "Introduction: motivation, a short review of the literature, statement of the problem.",
            "Theory: derivations, calculations, formulas.",
            "Practical part: simulation, data analysis, calculations.",
            "Discussion: plots, tables, interpretation of the results.",
            "Conclusions: the main results and how the work could be continued.",
            "References: all sources used.",
        ],
        "tools": "Technical aspects",
        "tools_items": [
            "Write the project in LaTeX; the online service overleaf.com is convenient.",
            "Feynman diagrams: the tikz-feynman package.",
            "Plots: the matplotlib library.",
        ],
        "book_line": "Textbook for the course:",
        "book_label": "“Quantum Field Theory for Experimentalists and Beyond” →",
        "book_href": "/en/materials.html#qft-book",
        "of": lambda i, n: f"project {i} of {n}",
        "prev": "Previous", "next": "Next", "all": "← All projects",
        "refs": "References", "files": "Files for the project",
        "pdf_title": "Examination projects in quantum field theory",
        "author": "D.~V.~Naumov",
        "toc": "Contents",
        "description": "Examination projects of D. V. Naumov's course in quantum field theory: autumn and spring problems with theory, calculation and simulation.",
    },
}


def plural_ru(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def e(text: str) -> str:
    return html.escape(text, quote=True)


# ------------------------------------------------------------------ sources

def strip_comments(tex: str) -> str:
    out = []
    for line in tex.splitlines():
        if line.lstrip().startswith("%"):
            continue
        out.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(out)


def braced(text: str, start: int) -> tuple[str, int]:
    """The contents of the {...} group that opens at text[start]; returns (contents, index after the group)."""
    assert text[start] == "{", text[start:start + 20]
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{" and text[i - 1] != "\\":
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
    raise ValueError("unbalanced braces")


def split_title(body: str) -> tuple[str, str]:
    """A project starts with \\section{Title}."""
    m = re.search(r"\\section\s*(?=\{)", body)
    if not m:
        raise ValueError("a project must start with \\section{...}")
    title, end = braced(body, m.end())
    return title.strip(), body[end:].strip()


def load_projects(book: Path, lang: str) -> dict[str, list[dict]]:
    base = book if lang == "ru" else book / "en"
    seasons: dict[str, list[dict]] = {"autumn": [], "spring": []}

    master = strip_comments((base / "chapters" / "Exams1.tex").read_text(encoding="utf-8"))
    topic = ""
    for m in re.finditer(r"\\chapter\{([^}]*)\}|\\input\{projects/([^}]+?)(?:\.tex)?\}", master):
        if m.group(1) is not None:
            topic = m.group(1).strip()
            continue
        name = m.group(2)
        title, body = split_title(strip_comments((base / "projects" / f"{name}.tex").read_text(encoding="utf-8")))
        seasons["autumn"].append({"slug": AUTUMN_SLUGS[name], "source": f"projects/{name}.tex",
                                  "title": title, "topic": topic, "body": body})

    spring = strip_comments((base / "chapters" / "Exams2.tex").read_text(encoding="utf-8"))
    spring = spring[spring.index("\\section{"):spring.index("\\end{mychapter}")]
    parts = re.split(r"(?=\\section\{)", spring)
    parts = [p for p in parts if p.strip()]
    if len(parts) != len(SPRING_SLUGS):
        raise SystemExit(f"{lang}: {len(parts)} spring projects, expected {len(SPRING_SLUGS)}")
    for slug, part in zip(SPRING_SLUGS, parts):
        title, body = split_title(part)
        seasons["spring"].append({"slug": slug, "source": "chapters/Exams2.tex", "title": title, "topic": "", "body": body})
    return seasons


# --------------------------------------------------------------- references

def parse_bib(path: Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        start = text.index("{", m.start())
        try:
            body, _ = braced(text, start)
        except ValueError:
            continue
        fields = {"type": m.group(1).lower()}
        for f in re.finditer(r"(\w+)\s*=\s*(?=\{)", body):
            value, _ = braced(body, f.end())
            fields[f.group(1).lower()] = value
        entries[m.group(2)] = fields
    return entries


def tex_to_text(value: str) -> str:
    value = re.sub(r"\\(?:textit|emph|textbf)\{([^{}]*)\}", r"\1", value)
    value = value.replace("~", " ").replace("\\&", "&").replace("--", "–")
    value = re.sub(r"[{}]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def format_ref(entry: dict[str, str]) -> str:
    """One line of the list of references (Markdown)."""
    authors = [tex_to_text(a) for a in entry.get("author", "").split(" and ") if a.strip()]
    names = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    title = tex_to_text(entry.get("title", ""))
    bits = [b for b in (names, f"*{title}*" if title else "") if b]
    journal = tex_to_text(entry.get("journal", ""))
    if journal:
        bits.append(" ".join(x for x in (journal, f"**{entry['volume']}**" if entry.get("volume") else "",
                                         tex_to_text(entry.get("pages", ""))) if x))
    if entry.get("year"):
        bits.append(f"({entry['year']})")
    line = ", ".join(bits[:-1]) + " " + bits[-1] if len(bits) > 1 and bits[-1].startswith("(") else ", ".join(bits)
    url = entry.get("url") or (f"https://doi.org/{entry['doi']}" if entry.get("doi") else "")
    if url:
        line += f" <{url}>"
    return line


# ------------------------------------------------------------- conversion

def checklists(tex: str) -> str:
    """Runs of paragraphs that start with \\faCheck become an itemize list."""
    out, run = [], []
    for para in re.split(r"\n\s*\n", tex):
        stripped = para.strip()
        if stripped.startswith("\\faCheck"):
            run.append(re.sub(r"^\\faCheck\s*(\\,)?\s*", "", stripped))
            continue
        if run:
            out.append("\\begin{itemize}\n" + "\n".join(f"\\item {r}" for r in run) + "\n\\end{itemize}")
            run = []
        out.append(para)
    if run:
        out.append("\\begin{itemize}\n" + "\n".join(f"\\item {r}" for r in run) + "\n\\end{itemize}")
    return "\n\n".join(out)


def lettered(tex: str) -> str:
    """An itemize whose items are labelled \\item[(a)], \\item[(b)], ... becomes a lettered enumerate."""
    def fix(m: re.Match) -> str:
        block = m.group(0)
        if not re.search(r"\\item\[\([a-z]\)\]", block):
            return block
        block = re.sub(r"\\item\[\([a-z]\)\]", r"\\item", block)
        return block.replace("\\begin{itemize}", "\\begin{enumerate}[(a)]", 1).replace("\\end{itemize}", "\\end{enumerate}")
    return re.sub(r"\\begin\{itemize\}(?:(?!\\begin\{itemize\}).)*?\\end\{itemize\}", fix, tex, flags=re.S)


MACROS = r"""\newcommand{\bm}[1]{\boldsymbol{#1}}
\newcommand{\Tr}[1]{\operatorname{Tr}\left(#1\right)}
"""
# contraction with gamma matrices, as in the book: a hat in Russian (dvn.sty), the Feynman slash in English (dvn-en.sty)
FSL = {"ru": r"\newcommand{\fsl}[1]{\hat{#1}}" + "\n", "en": r"\newcommand{\fsl}[1]{\cancel{#1}}" + "\n"}


def to_markdown(body: str, lang: str, refs: list[str]) -> str:
    tex = body
    tex = re.sub(r"\\index\{[^{}]*\}", "", tex)
    tex = re.sub(r"\\label\{[^{}]*\}", "", tex)
    tex = re.sub(r"\\(newpage|medskip|bigskip|smallskip|noindent|clearpage)\b", "", tex)
    tex = re.sub(r"\\begin\{(equation\*?)\}", r"\\[", tex)
    tex = re.sub(r"\\end\{(equation\*?)\}", r"\\]", tex)
    if lang == "ru":
        tex = tex.replace("<<", "«").replace(">>", "»")

    def cite(m: re.Match) -> str:
        marks = []
        for key in (k.strip() for k in m.group(1).split(",")):
            if key not in refs:
                refs.append(key)
            n = refs.index(key) + 1
            marks.append(f"\\href{{\\#ref-{n}}}{{[{n}]}}")
        return " " + ", ".join(marks)

    tex = re.sub(r"~?\\cite\{([^}]*)\}", cite, tex)
    tex = checklists(tex)
    tex = lettered(tex)
    md = subprocess.run(["quarto", "pandoc", "-f", "latex", "-t", "markdown-raw_tex", "--wrap=none"],
                        input=MACROS + FSL[lang] + tex, capture_output=True, text=True, check=True).stdout
    md = md.replace("(\\#ref-", "(#ref-")
    # headings inside a project start at level 2 (the page title is h1)
    return md.strip() + "\n"


# ------------------------------------------------------------------- pages

def season_pdf(season: str, lang: str) -> str:
    return f"qft-exams-{season}-{lang}.pdf"


def project_page(lang: str, season: str, items: list[dict], index: int, bib: dict) -> str:
    t = T[lang]
    item = items[index]
    refs: list[str] = []
    body = to_markdown(item["body"], lang, refs)
    n = len(items)
    title = tex_inline(item["title"])
    meta = t["season"][season] + " · " + t["of"](index + 1, n)
    topic = f'<p class="course-toc-meta">{t["topic"]}: {e(tex_inline(item["topic"]))}</p>' if item["topic"] else ""
    out = [
        "---",
        f'pagetitle: "{plain(title)} — {t["short"]}"',
        f"lang: {t['lang']}",
        f'description: "{plain(title)}: {t["short"].lower()} — {t["season"][season].lower()}."',
        "toc: false",
        "---",
        "",
        "```{=html}",
        f'<article class="course-page qft-exam-page">',
        f'  <nav class="course-crumbs" aria-label="breadcrumbs"><a href="../index.html">{t["site"]}</a><span>›</span>'
        f'<a href="../education.html">{t["education"]}</a><span>›</span>'
        f'<a href="../qft-exams.html">{t["short"]}</a><span>›</span>'
        f'<a href="../qft-exams.html#{season}">{t["season"][season]}</a></nav>',
        '  <header class="course-page-head">',
        f'    <span class="course-tile-status is-ready">{e(meta)}</span>',
        f"    <h1>{html_inline(item['title'])}</h1>",
        f"    {topic}" if topic else None,
        "  </header>",
        "```",
        "",
        "::: {.qft-exam-body}",
        body,
    ]
    if refs:
        out += [f"## {t['refs']}", ""]
        for i, key in enumerate(refs, 1):
            if key not in bib:
                raise SystemExit(f"{lang}: unknown reference {key}")
            out.append(f"[{i}]{{#ref-{i}}} {format_ref(bib[key])}" + "\\")
        out[-1] = out[-1].rstrip("\\")
        out.append("")
    files = FILES.get(item["slug"])
    out += [":::", "", "```{=html}"]
    actions = []
    for name, label in files or []:
        actions.append(f'<a class="lecture-action-primary" href="../../assets/qft-exams/{name}" download>{e(label[lang])}</a>')
    actions.append(f'<a href="../../assets/qft-exams/{season_pdf(season, lang)}">{e(t["pdf_season"](t["season"][season]))}</a>')
    out.append(f'  <div class="lecture-course-actions qft-exam-actions">{"".join(actions)}</div>')
    prev_link = (f'<a class="qft-exam-prev" href="{items[index - 1]["slug"]}.html"><span>← {t["prev"]}</span>'
                 f'{html_inline(items[index - 1]["title"])}</a>') if index > 0 else "<span></span>"
    next_link = (f'<a class="qft-exam-next" href="{items[index + 1]["slug"]}.html"><span>{t["next"]} →</span>'
                 f'{html_inline(items[index + 1]["title"])}</a>') if index < n - 1 else "<span></span>"
    out += [f'  <nav class="qft-exam-nav">{prev_link}{next_link}</nav>',
            f'  <p class="course-page-back"><a href="../qft-exams.html#{season}">{t["all"]}</a></p>',
            "</article>", "```", ""]
    return "\n".join(line for line in out if line is not None)


def tex_inline(text: str) -> str:
    """A title for plain-text places (page title, attributes): math kept as TeX."""
    return re.sub(r"\\\((.*?)\\\)", r"$\1$", text).replace("~", " ").replace("--", "–")


GREEK = {"pi": "π", "gamma": "γ", "sigma": "σ", "nu": "ν", "mu": "μ", "phi": "φ", "lambda": "λ", "theta": "θ"}


def plain(text: str) -> str:
    """A title without TeX (for <title> and the description)."""
    def math(m: re.Match) -> str:
        s = re.sub(r"\\([a-zA-Z]+)\s*", lambda g: GREEK.get(g.group(1), ""), m.group(1))
        s = s.replace("^+", "⁺").replace("^-", "⁻")
        return re.sub(r"[{}^_\\ ]", "", s)
    return re.sub(r"\$([^$]*)\$", math, text).replace('"', "'")


def html_inline(text: str) -> str:
    """A title in HTML: math as \\( ... \\) for MathJax."""
    text = tex_inline(text)
    return re.sub(r"\$([^$]*)\$", lambda m: f"\\({e(m.group(1))}\\)", e(text).replace("$", "$"))


def list_page(lang: str, seasons: dict[str, list[dict]]) -> str:
    t = T[lang]
    total = {s: len(seasons[s]) for s in SEASONS}
    out = [
        "---",
        f'pagetitle: "{t["title"]}"',
        f"lang: {t['lang']}",
        f'description: "{t["description"]}"',
        "toc: false",
        "---",
        "",
        "```{=html}",
        '<article class="course-page qft-exams">',
        f'  <nav class="course-crumbs" aria-label="breadcrumbs"><a href="index.html">{t["site"]}</a><span>›</span>'
        f'<a href="education.html">{t["education"]}</a><span>›</span><span>{t["short"]}</span></nav>',
        '  <header class="course-page-head">',
        f'    <span class="course-tile-status is-ready">{t["kind"]}</span>',
        f'    <h1>{t["title"]}</h1>',
        f'    <p class="course-page-summary">{e(t["lead"])}</p>',
        f'    <p class="course-toc-meta">{t["season"]["autumn"]} · {t["projects"](total["autumn"])} · '
        f'{t["season"]["spring"]} · {t["projects"](total["spring"])}</p>',
        '    <div class="lecture-course-actions">'
        + "".join(f'<a class="lecture-action-primary" href="#{s}">{t["season"][s]}</a>' for s in SEASONS)
        + "".join(f'<a href="../assets/qft-exams/{season_pdf(s, lang)}">{e(t["pdf_season"](t["season"][s]))}</a>'
                  for s in SEASONS)
        + "</div>",
        "  </header>",
    ]
    for season in SEASONS:
        items = seasons[season]
        out += [f'  <h2 id="{season}" class="course-page-section">{t["season_long"][season]} · {t["projects"](len(items))}</h2>',
                f'  <p class="course-page-summary qft-exams-season-lead">{e(t["season_lead"][season])}</p>',
                '  <table class="course-toc course-toc-full qft-exams-toc">',
                f'    <thead><tr><th class="course-toc-num">{t["num"]}</th><th>{t["project"]}</th>'
                + (f'<th class="qft-exams-topic">{t["topic"]}</th>' if season == "autumn" else "") + "</tr></thead>",
                "    <tbody>"]
        for i, item in enumerate(items, 1):
            topic = f'<td class="qft-exams-topic">{e(tex_inline(item["topic"]))}</td>' if season == "autumn" else ""
            out.append(f'      <tr id="{item["slug"]}"><td class="course-toc-num">{i:02d}</td>'
                       f'<td class="course-toc-topic"><a href="qft-exams/{item["slug"]}.html">{html_inline(item["title"])}</a></td>'
                       f"{topic}</tr>")
        out += ["    </tbody>", "  </table>"]
    out += [f'  <h2 id="how" class="course-page-section">{t["how"]}</h2>',
            '  <div class="qft-exams-how">']
    for key in ("goals", "structure", "tools"):
        tag = "ol" if key == "structure" else "ul"
        items_html = "".join(f"<li>{e(x)}</li>" for x in t[f"{key}_items"])
        out.append(f'    <div class="course-page-card"><h3>{t[key]}</h3><{tag}>{items_html}</{tag}></div>')
    out += ["  </div>",
            f'  <p class="course-page-note">{e(t["updated"])}</p>',
            f'  <p class="course-book-line">{e(t["book_line"])} <a href="{t["book_href"].replace("/" + lang + "/", "")}">{e(t["book_label"])}</a></p>',
            f'  <p class="course-page-back"><a href="education.html">← {t["education"]}</a></p>',
            "</article>", "```", ""]
    return "\n".join(out)


# --------------------------------------------------------------------- PDF

PDF_PREAMBLE = r"""%% Generated by neutrinohit-map/scripts/build_qft_exams.py
\documentclass[11pt,a4paper]{article}
\usepackage[libertine]{newtxmath}
\usepackage[nomath]{libertinus}
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{<MAIN>}
\setotherlanguage{<OTHER>}
\usepackage{amsmath,mathtools,bm}
\usepackage{enumitem}
\usepackage{fontawesome5}
\usepackage[a4paper,left=24mm,right=24mm,top=22mm,bottom=24mm]{geometry}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\definecolor{nhteal}{HTML}{1F6F78}
\titleformat{\section}{\Large\bfseries\color{nhteal}}{\thesection.}{0.6em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection.}{0.5em}{}
\setlist{itemsep=2pt,topsep=4pt}
\newcommand{\Tr}[1]{\text{Tr}\left(#1\right)}
<FSL>
\setlength{\parskip}{0.35em}
\setlength{\parindent}{0pt}
\setlength{\emergencystretch}{3em}
\hypersetup{pdftitle={<TITLE>},pdfauthor={<AUTHORPDF>}}
\begin{document}
"""


def pdf_source(lang: str, season: str, items: list[dict], bib: dict) -> str:
    t = T[lang]
    main, other = ("russian", "english") if lang == "ru" else ("english", "russian")
    title = f'{t["pdf_title"]}. {t["season"][season]}'
    src = (PDF_PREAMBLE.replace("<MAIN>", main).replace("<OTHER>", other)
           .replace("<TITLE>", title).replace("<AUTHORPDF>", t["author"].replace("~", " "))
           .replace("<FSL>", r"\newcommand{\fsl}[1]{\hat{#1}}" if lang == "ru"
                    else r"\usepackage{slashed}" + "\n" + r"\newcommand{\fsl}[1]{\slashed{#1}}"))
    src += "\\begin{center}\n{\\LARGE\\bfseries " + t["pdf_title"] + "}\\\\[0.4em]\n{\\Large " + t["season_long"][season] + "}\\\\[0.8em]\n"
    src += t["author"] + "\\\\[0.2em]\\small\\url{" + f"{BASE_URL}/{lang}/qft-exams.html" + "}\n\\end{center}\n\n"
    src += t["lead"].replace("«", "<<").replace("»", ">>") + "\n\n"
    for key in ("goals", "structure", "tools"):
        env = "enumerate" if key == "structure" else "itemize"
        src += f"\\paragraph{{{t[key]}}}\n\\begin{{{env}}}\n" + "".join(
            f"\\item {latex_escape(x)}\n" for x in t[f"{key}_items"]) + f"\\end{{{env}}}\n"
    src += "\n\\renewcommand{\\contentsname}{" + t["toc"] + "}\n\\tableofcontents\n"
    refs: list[str] = []
    topic = None
    for item in items:
        src += "\n\\clearpage\n"
        if item["topic"] and item["topic"] != topic:
            topic = item["topic"]
            src += f"\\addcontentsline{{toc}}{{part}}{{{topic}}}\n"
            src += f"{{\\small\\color{{gray}}{topic}}}\\par\n"
        body = item["body"]
        for key in re.findall(r"\\cite\{([^}]*)\}", body):
            for k in key.split(","):
                if k.strip() not in refs:
                    refs.append(k.strip())
        src += f"\\section{{{item['title']}}}\n{body}\n"
    if refs:
        src += "\n\\clearpage\n\\begin{thebibliography}{99}\n"
        for key in refs:
            src += f"\\bibitem{{{key}}} {bib_latex(bib[key])}\n"
        src += "\\end{thebibliography}\n"
    src += "\\end{document}\n"
    return src


def latex_escape(text: str) -> str:
    return text.replace("LaTeX", "\\LaTeX{}").replace("«", "<<").replace("»", ">>")


def bib_latex(entry: dict[str, str]) -> str:
    authors = [a.strip() for a in entry.get("author", "").split(" and ") if a.strip()]
    parts = []
    if authors:
        parts.append(", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""))
    if entry.get("title"):
        parts.append("\\textit{" + entry["title"] + "}")
    if entry.get("journal"):
        parts.append(" ".join(x for x in (entry["journal"], "\\textbf{" + entry["volume"] + "}" if entry.get("volume") else "",
                                         entry.get("pages", "")) if x))
    line = ", ".join(parts)
    if entry.get("year"):
        line += f" ({entry['year']})"
    if entry.get("url"):
        line += ". \\url{" + entry["url"] + "}"
    return line + "."


def build_pdf(lang: str, season: str, items: list[dict], bib: dict, book: Path) -> None:
    src = pdf_source(lang, season, items, bib)
    with tempfile.TemporaryDirectory() as tmp:
        tex = Path(tmp) / f"qft-exams-{season}-{lang}.tex"
        tex.write_text(src, encoding="utf-8")
        result = subprocess.run(["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                                cwd=tmp, capture_output=True, text=True)
        log = tex.with_suffix(".log")
        keep = SITE_ROOT / ".work" / "qft-exams"          # the source and the log of the last build (git-ignored)
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copy(tex, keep / tex.name)
        if log.exists():
            shutil.copy(log, keep / log.name)
        if result.returncode != 0:
            raise SystemExit(f"LaTeX failed for {tex.name}; see {keep}")
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(tex.with_suffix(".pdf"), ASSET_DIR / season_pdf(season, lang))
        print(f"wrote {ASSET_DIR / season_pdf(season, lang)}")


# -------------------------------------------------------------------- main

def outputs(book: Path, langs: tuple[str, ...] = LANGS) -> tuple[dict[Path, str], dict]:
    files: dict[Path, str] = {}
    data = {}
    for lang in langs:
        seasons = load_projects(book, lang)
        bib = parse_bib(book / ("references.bib" if lang == "ru" else "en/references.bib"))
        data[lang] = (seasons, bib)
        files[SITE_ROOT / lang / "qft-exams.qmd"] = list_page(lang, seasons)
        for season in SEASONS:
            items = seasons[season]
            for i, item in enumerate(items):
                files[SITE_ROOT / lang / "qft-exams" / f"{item['slug']}.qmd"] = project_page(lang, season, items, i, bib)
    if len(data) == len(LANGS):
        ru, en = data["ru"][0], data["en"][0]
        for season in SEASONS:
            if [i["slug"] for i in ru[season]] != [i["slug"] for i in en[season]]:
                raise SystemExit(f"{season}: the Russian and English projects differ")
    return files, data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--thebook", type=Path, default=SITE_ROOT.parent / "TheBook")
    parser.add_argument("--pdf", action="store_true", help="also build the PDFs of the seasons")
    parser.add_argument("--check", action="store_true", help="only check that the pages are up to date")
    parser.add_argument("--lang", choices=LANGS, help="one language only (a draft; --check needs both)")
    args = parser.parse_args()
    files, data = outputs(args.thebook, (args.lang,) if args.lang else LANGS)
    stale = [p for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"stale: {p.relative_to(SITE_ROOT)}")
        return 1 if stale else 0
    for lang in data:
        folder = SITE_ROOT / lang / "qft-exams"
        if folder.is_dir():
            for old in folder.glob("*.qmd"):
                if old not in files:
                    old.unlink()
                    print(f"removed {old.relative_to(SITE_ROOT)}")
    for p in stale:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(files[p], encoding="utf-8")
        print(f"wrote {p.relative_to(SITE_ROOT)}")
    print(f"{len(files)} pages, {len(stale)} changed")
    if args.pdf:
        for lang in data:
            seasons, bib = data[lang]
            for season in SEASONS:
                build_pdf(lang, season, seasons[season], bib, args.thebook)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
