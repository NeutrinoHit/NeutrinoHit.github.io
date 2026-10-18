#!/usr/bin/env python3
"""Compare or refresh the local copies of the shared Reveal assets.

Canonical files live in neutrinohit-map/assets/reveal. Each consumer keeps
copies in its own repository:

  <repo>/shared/reveal/   footer, timed captions, quiz CSS, logo
  <repo>/shared/styles/   neutrinohit-reveal.scss

Examples:

  python scripts/sync_reveal_assets.py --check --all
  python scripts/sync_reveal_assets.py --check --target talks --diff
  python scripts/sync_reveal_assets.py --target gravity --target talks
  python scripts/sync_reveal_assets.py --all

Without --target/--all the script keeps its historical behaviour: it writes
the legacy default set (the seven original Reveal targets and five style
targets); see --list.
"""

from __future__ import annotations

import sys

from asset_sync import Consumer, Copy, WORKSPACE, build_parser, run


SOURCE = WORKSPACE / "neutrinohit-map" / "assets" / "reveal"

REVEAL_FILES = [
    "neutrinohit-reveal-footer.js",
    "neutrinohit-timed-captions.js",
    "neutrinohit-reveal-quiz.css",
    "dvnlogo.png",
]

STYLE_FILE = "neutrinohit-reveal.scss"

# Repositories that received the files when the script ran without arguments.
LEGACY_REVEAL = {
    "talks",
    "qft-lectures",
    "gravity",
    "sciencepop",
    "stat-course",
    "neutrinophysics",
    "particlephysics",
}
LEGACY_STYLE = {"talks", "qft-lectures", "gravity", "neutrinophysics", "particlephysics"}

REPOSITORIES = [
    "talks",
    "qft-lectures",
    "gravity",
    "sciencepop",
    "stat-course",
    "neutrinophysics",
    "particlephysics",
    "numerical_methods",
    "rte_lectures",
]


# Consumer copies that carry rules not yet moved out of the shared file.
HOLDS: dict[tuple[str, str], str] = {}


def standard_copies(repo: str) -> list[Copy]:
    copies = [
        Copy(name, "shared/reveal", legacy=repo in LEGACY_REVEAL) for name in REVEAL_FILES
    ]
    copies.append(
        Copy(
            STYLE_FILE,
            "shared/styles",
            legacy=repo in LEGACY_STYLE,
            hold=HOLDS.get((repo, STYLE_FILE), ""),
        )
    )
    return copies


def consumers() -> list[Consumer]:
    return [Consumer(repo, standard_copies(repo)) for repo in REPOSITORIES]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(__doc__.splitlines()[0], "\n".join(__doc__.splitlines()[2:]))
    args = parser.parse_args(argv)
    return run(SOURCE, consumers(), args, "scripts/sync_reveal_assets.py")


if __name__ == "__main__":
    sys.exit(main())
