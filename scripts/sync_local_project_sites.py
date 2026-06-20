#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "_site"


@dataclass(frozen=True)
class ProjectSite:
    slug: str
    source: Path


PROJECT_SITES = [
    ProjectSite("talks", WORKSPACE / "talks" / "_site"),
    ProjectSite("qft-lectures", WORKSPACE / "qft-lectures" / "_site"),
    ProjectSite("sciencepop", WORKSPACE / "sciencepop" / "_site"),
    ProjectSite("neutrinophysics", WORKSPACE / "neutrinophysics" / "_site"),
    ProjectSite("particlephysics", WORKSPACE / "particlephysics" / "_site"),
    ProjectSite("statistical-analysis-course", WORKSPACE / "stat-course" / "pages"),
]


def should_skip() -> bool:
    if os.environ.get("GITHUB_ACTIONS"):
        return True
    return os.environ.get("NEUTRINOHIT_SYNC_PROJECT_SITES", "1") in {"0", "false", "False"}


def copy_site(site: ProjectSite) -> None:
    if not site.source.exists():
        print(f"[local-preview] skip missing {site.source}")
        return

    target = OUT / site.slug
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(site.source, target, ignore=shutil.ignore_patterns(".git", ".quarto"))
    print(f"[local-preview] {site.source} -> {target}")


def main() -> None:
    if should_skip():
        print("[local-preview] skipped")
        return

    OUT.mkdir(parents=True, exist_ok=True)
    for site in PROJECT_SITES:
        copy_site(site)


if __name__ == "__main__":
    main()
