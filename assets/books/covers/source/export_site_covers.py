#!/usr/bin/env python3
"""Render the front covers of the books in progress as small JPEG images for the Books page.

The site shows each book in progress as a card with its front cover. Books with a
published cover export (published/) use that font-independent SVG; the other books use
their current series SVG (svg/v1/). The JPEG files go to assets/books/series/ and are
outputs of this script: change the covers, then run

  python assets/books/covers/source/export_site_covers.py
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT.parent / "series"
WIDTH = 400
COVERS = {
    "statistical_methods": ROOT / "published/statistical_methods_front.svg",
    "neutrino_physics": ROOT / "published/neutrino_physics_front.svg",
    "particle_physics": ROOT / "svg/v1/particle_physics_front.svg",
    "gravity": ROOT / "svg/v1/gravity_front.svg",
    "numerical_methods": ROOT / "svg/v1/numerical_methods_front.svg",
}


def main() -> None:
    for command in ("rsvg-convert", "magick"):
        if not shutil.which(command):
            raise SystemExit(f"Required for the site covers: {command}")
    DESTINATION.mkdir(exist_ok=True)
    for slug, source in COVERS.items():
        target = DESTINATION / f"{slug.replace('_', '-')}-front.jpg"
        with tempfile.TemporaryDirectory(prefix="site-cover-") as temporary:
            png = Path(temporary) / "cover.png"
            subprocess.run(["rsvg-convert", "--width", str(WIDTH), "--background-color", "white",
                            "--output", str(png), str(source)], check=True)
            subprocess.run(["magick", str(png), "-strip", "-interlace", "Plane", "-sampling-factor", "4:2:0",
                            "-quality", "84", str(target)], check=True)
        print(target.relative_to(ROOT.parents[2]))


if __name__ == "__main__":
    main()
