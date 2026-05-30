#!/usr/bin/env python3
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "neutrinohit-map" / "assets" / "reveal"

TARGETS = [
    ROOT / "talks" / "shared" / "reveal",
    ROOT / "qft-lectures" / "shared" / "reveal",
    ROOT / "sciencepop" / "shared" / "reveal",
    ROOT / "stat-course" / "ru" / "slides" / "shared" / "reveal",
    ROOT / "stat-course" / "en" / "slides" / "shared" / "reveal",
]

FILES = [
    "neutrinohit-reveal-footer.js",
    "dvnlogo.png",
]


def main() -> None:
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            shutil.copy2(SOURCE / name, target / name)
            print(f"{SOURCE / name} -> {target / name}")


if __name__ == "__main__":
    main()
