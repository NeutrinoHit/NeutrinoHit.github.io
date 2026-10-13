#!/usr/bin/env python3
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "neutrinohit-map" / "assets" / "books"

TARGETS = {
    "neutrinohit-book.css": [
        ROOT / "stat-course" / "ru" / "book" / "assets" / "styles",
        ROOT / "neutrinophysics" / "introduction" / "ru" / "book" / "assets" / "styles",
    ],
    "neutrinohit-book.tex": [
        ROOT / "stat-course" / "shared" / "latex",
        ROOT / "neutrinophysics" / "shared" / "latex",
    ],
    "neutrinohit-book.lua": [
        ROOT / "stat-course" / "ru" / "book" / "assets" / "filters",
        ROOT / "neutrinophysics" / "introduction" / "ru" / "book" / "assets" / "filters",
    ],
}


def main() -> None:
    for name, target_directories in TARGETS.items():
        source = SOURCE / name
        if not source.exists():
            raise FileNotFoundError(f"Missing shared asset: {source}")
        for target_directory in target_directories:
            target = target_directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"{source} -> {target}")


if __name__ == "__main__":
    main()
