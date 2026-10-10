#!/usr/bin/env python3
"""Publish font-independent vector covers and sync only their book assets."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[3]
BOOKS = {
    "statistical_methods": WORKSPACE / "stat-course/ru/book/assets/covers",
    "neutrino_physics": WORKSPACE / "neutrinophysics/introduction/ru/book/assets/covers",
}
SVG = "{http://www.w3.org/2000/svg}"


def print_geometry(source: Path, target: Path) -> None:
    """Express the binary black-hole cutout as an equivalent vector clip."""
    tree = ET.parse(source)
    clips = set()
    for mask in tree.iter(f"{SVG}mask"):
        if not mask.get("id", "").endswith("bh-exterior-only"):
            raise ValueError(f"Unreviewed SVG mask: {mask.get('id')}")
        rectangle, circle = list(mask)
        if rectangle.tag != f"{SVG}rect" or circle.tag != f"{SVG}circle":
            raise ValueError("Expected rectangular mask with circular shadow cutout")
        if (rectangle.get("fill") != "#fff" or circle.get("fill") != "#000"
                or float(circle.get("cx", 0)) != 0 or float(circle.get("cy", 0)) != 0):
            raise ValueError("Expected a binary mask with a centred circular cutout")
        x, y, w, h = [float(rectangle.get(key)) for key in ("x", "y", "width", "height")]
        radius = float(circle.get("r"))
        identifier = mask.get("id")
        clips.add(f"url(#{identifier})")
        mask.clear()
        mask.tag = f"{SVG}clipPath"
        mask.attrib.update(id=identifier, clipPathUnits="userSpaceOnUse")
        ET.SubElement(mask, f"{SVG}path", {
            "clip-rule": "evenodd",
            "d": f"M{x},{y}h{w}v{h}h{-w}Z M{-radius},0a{radius},{radius} 0 1 0 {2*radius},0a{radius},{radius} 0 1 0 {-2*radius},0Z",
        })
    for element in tree.iter():
        if element.get("mask") in clips:
            element.set("clip-path", element.attrib.pop("mask"))
    tree.write(target, encoding="utf-8", xml_declaration=True)


def export() -> None:
    inkscape = os.environ.get("INKSCAPE", "inkscape")
    for command in ("rsvg-convert", "pdfimages", inkscape):
        if not shutil.which(command):
            raise SystemExit(f"Required for cover export: {command}")
    destination = ROOT / "published"
    destination.mkdir(exist_ok=True)
    for book in BOOKS:
        for side in ("front", "back"):
            stem = f"{book}_{side}"
            pdf = destination / f"{stem}.pdf"
            svg = destination / f"{stem}.svg"
            with tempfile.TemporaryDirectory(prefix="book-cover-") as temporary:
                prepared = Path(temporary) / f"{stem}.svg"
                print_geometry(ROOT / "svg/v2" / f"{stem}.svg", prepared)
                subprocess.run([
                    inkscape, str(prepared), "--export-type=svg",
                    "--export-plain-svg", "--export-text-to-path",
                    f"--export-filename={svg}",
                ], check=True)
            tree = ET.parse(svg)
            if list(tree.iter(f"{SVG}image")) or list(tree.iter(f"{SVG}text")):
                raise ValueError(f"Not a font-independent vector export: {svg}")
            subprocess.run([
                "rsvg-convert", "--format=pdf", "--output", str(pdf), str(svg),
            ], check=True, env={**os.environ, "SOURCE_DATE_EPOCH": "1788566400"})
            images = subprocess.check_output(["pdfimages", "-list", str(pdf)], text=True)
            if any(line.split() and line.split()[0].isdigit() for line in images.splitlines()):
                raise ValueError(f"Raster content in PDF cover: {pdf}")
            print(pdf.relative_to(ROOT), svg.relative_to(ROOT))


def sync(check: bool) -> None:
    for book, destination in BOOKS.items():
        if not destination.parents[2].is_dir():
            raise FileNotFoundError(f"Book checkout is missing: {destination}")
        sources = {
            f"{side}.{extension}": ROOT / "published" / f"{book}_{side}.{extension}"
            for side in ("front", "back") for extension in ("svg", "pdf")
        }
        sources.update({name: ROOT / "integration" / name
                        for name in ("covers.css", "covers.tex", "back-cover.tex", "README.md")})
        for name, source in sources.items():
            target = destination / name
            if check:
                if not target.exists() or source.read_bytes() != target.read_bytes():
                    raise ValueError(f"Stale or missing cover asset: {target}")
            else:
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        print(f"{'Checked' if check else 'Synced'} {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="copy existing exports only")
    parser.add_argument("--check-sync", action="store_true", help="compare without writing")
    args = parser.parse_args()
    if args.sync or args.check_sync:
        sync(args.check_sync)
    else:
        export()
