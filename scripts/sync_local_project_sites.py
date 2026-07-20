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
    static_source: bool = False
    overlays: tuple[tuple[Path, str], ...] = ()


PROJECT_SITES = [
    ProjectSite("talks", WORKSPACE / "talks" / "_site"),
    ProjectSite("qft-lectures", WORKSPACE / "qft-lectures" / "_site"),
    ProjectSite("sciencepop", WORKSPACE / "sciencepop", static_source=True),
    ProjectSite("neutrinophysics", WORKSPACE / "neutrinophysics" / "_site"),
    ProjectSite("particlephysics", WORKSPACE / "particlephysics" / "_site"),
    ProjectSite(
        "statistical-analysis-course",
        WORKSPACE / "stat-course" / "pages",
        overlays=(
            (WORKSPACE / "stat-course" / "ru" / "slides" / "_site", "ru/slides"),
            (WORKSPACE / "stat-course" / "en" / "slides" / "_site", "en/slides"),
            (WORKSPACE / "stat-course" / "ru" / "book" / "_book", "ru/book"),
            (WORKSPACE / "stat-course" / "en" / "book" / "_book", "en/book"),
        ),
    ),
]


def should_skip() -> bool:
    if os.environ.get("GITHUB_ACTIONS"):
        return True
    return os.environ.get("NEUTRINOHIT_SYNC_PROJECT_SITES", "1") in {"0", "false", "False"}


def is_conflict_copy(name: str) -> bool:
    base, sep, suffix = name.rpartition(" ")
    return bool(base and sep and suffix.isdigit())


def copy_available(src: str, dst: str) -> str:
    try:
        shutil.copy2(src, dst)
    except OSError as exc:
        if getattr(exc, "errno", None) == 60 or "Operation timed out" in str(exc):
            return dst
        raise
    return dst


def project_ignore(_: str, names: list[str]) -> set[str]:
    ignored = {".git", ".quarto", ".DS_Store"}
    ignored.update(name for name in names if is_conflict_copy(name) or name.endswith(".pdfp"))
    return ignored.intersection(names)


def sciencepop_ignore(_: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".github",
        ".quarto",
        "_site",
        ".DS_Store",
        ".gitignore",
        ".gitattributes",
        "harmonic_dynamics.png",
        "lira_bricks.py",
        "requirements.txt",
        "ideas.md",
    }
    ignored.update(name for name in names if name.endswith(".qmd") or name.endswith(".key") or is_conflict_copy(name))
    return ignored.intersection(names)


def prune_sciencepop_copy(target: Path) -> None:
    for rel in ["ModernPhysics/slides", "WaveOrParticle/obsolete"]:
        path = target / rel
        if path.exists():
            shutil.rmtree(path)
    (target / ".nojekyll").touch()


def overlay_sciencepop_build(target: Path) -> None:
    generated = WORKSPACE / "sciencepop" / "_site"
    if not generated.exists():
        print(f"[local-preview] skip missing sciencepop build {generated}")
        return
    shutil.copytree(
        generated,
        target,
        dirs_exist_ok=True,
        ignore=project_ignore,
        copy_function=copy_available,
    )


def copy_site(site: ProjectSite) -> None:
    if not site.source.exists():
        print(f"[local-preview] skip missing {site.source}")
        return

    target = OUT / site.slug
    if target.exists():
        shutil.rmtree(target)

    if site.static_source:
        shutil.copytree(site.source, target, ignore=sciencepop_ignore, copy_function=copy_available)
        if site.slug == "sciencepop":
            overlay_sciencepop_build(target)
        prune_sciencepop_copy(target)
    else:
        shutil.copytree(site.source, target, ignore=project_ignore, copy_function=copy_available)

    for overlay_source, overlay_rel in site.overlays:
        if not overlay_source.exists():
            print(f"[local-preview] skip missing overlay {overlay_source}")
            continue
        overlay_target = target / overlay_rel
        if overlay_target.exists():
            shutil.rmtree(overlay_target)
        shutil.copytree(overlay_source, overlay_target, ignore=project_ignore, copy_function=copy_available)
        print(f"[local-preview] {overlay_source} -> {overlay_target}")

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
