#!/usr/bin/env python3
"""Compare or refresh the local copies of the shared book assets.

Canonical files live in neutrinohit-map/assets/books: book CSS, LaTeX
preamble, the neutrinohit-book.lua filter (QR cards) and the shared filters
hide-book-index.lua and chapter-bibliographies.lua. Consumers keep them next
to each book:

  <book>/assets/styles/    neutrinohit-book.css
  <book>/assets/filters/   *.lua
  <repo>/shared/latex/     neutrinohit-book.tex

Examples:

  python scripts/sync_book_assets.py --check --all
  python scripts/sync_book_assets.py --check --target neutrinophysics --diff
  python scripts/sync_book_assets.py --target stat-course

Without --target/--all the script keeps its historical behaviour: it writes
the CSS, LaTeX preamble and neutrinohit-book.lua into stat-course and
neutrinophysics; see --list.
"""

from __future__ import annotations

import sys

from asset_sync import Consumer, Copy, WORKSPACE, build_parser, run


SOURCE = WORKSPACE / "neutrinohit-map" / "assets" / "books"

HIDE_INDEX_ALL = (
    "the local filter also hides the index heading in HTML; set "
    "`hide-book-index: all` in the book _quarto.yml first"
)


def book_copies(
    book: str,
    *,
    legacy: bool = False,
    filters: tuple[str, ...] = (),
    holds: dict[str, str] | None = None,
) -> list[Copy]:
    holds = holds or {}
    copies = [
        Copy("neutrinohit-book.css", f"{book}/assets/styles", legacy=legacy),
        Copy("neutrinohit-book.lua", f"{book}/assets/filters", legacy=legacy),
    ]
    copies += [
        Copy(name, f"{book}/assets/filters", hold=holds.get(name, "")) for name in filters
    ]
    return copies


def latex_copy(repo_latex: str, *, legacy: bool = False) -> Copy:
    return Copy("neutrinohit-book.tex", repo_latex, legacy=legacy)


def consumers() -> list[Consumer]:
    return [
        Consumer(
            "stat-course",
            book_copies(
                "ru/book",
                legacy=True,
                filters=("hide-book-index.lua", "chapter-bibliographies.lua"),
            )
            + [latex_copy("shared/latex", legacy=True)],
        ),
        Consumer(
            "neutrinophysics",
            book_copies(
                "introduction/ru/book",
                legacy=True,
                filters=("hide-book-index.lua",),
                holds={"hide-book-index.lua": HIDE_INDEX_ALL},
            )
            + [latex_copy("shared/latex", legacy=True)],
        ),
        Consumer(
            "gravity",
            book_copies("ru/book", filters=("hide-book-index.lua",)) + [latex_copy("shared/latex")],
        ),
        Consumer(
            "particlephysics",
            book_copies("ParticlePhysics/ru/book")
            + book_copies("ParticlePhysics/en/book")
            + [latex_copy("shared/latex")],
        ),
        Consumer(
            "numerical_methods",
            book_copies(
                "ru/book",
                filters=("hide-book-index.lua", "chapter-bibliographies.lua"),
            )
            + book_copies(
                "en/book",
                filters=("hide-book-index.lua", "chapter-bibliographies.lua"),
            )
            + [latex_copy("shared/latex")],
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(__doc__.splitlines()[0], "\n".join(__doc__.splitlines()[2:]))
    args = parser.parse_args(argv)
    return run(SOURCE, consumers(), args, "scripts/sync_book_assets.py")


if __name__ == "__main__":
    sys.exit(main())
