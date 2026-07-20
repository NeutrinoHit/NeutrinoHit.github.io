#!/usr/bin/env python3
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "neutrinohit-map" / "assets" / "reveal"

REVEAL_TARGETS = [
    ROOT / "talks" / "shared" / "reveal",
    ROOT / "qft-lectures" / "shared" / "reveal",
    ROOT / "sciencepop" / "shared" / "reveal",
    ROOT / "stat-course" / "shared" / "reveal",
    ROOT / "neutrinophysics" / "shared" / "reveal",
    ROOT / "particlephysics" / "shared" / "reveal",
]

STYLE_TARGETS = [
    ROOT / "qft-lectures" / "shared" / "styles",
    ROOT / "neutrinophysics" / "shared" / "styles",
    ROOT / "particlephysics" / "shared" / "styles",
]

REVEAL_FILES = [
    "neutrinohit-reveal-footer.js",
    "neutrinohit-timed-captions.js",
    "neutrinohit-reveal-quiz.css",
    "dvnlogo.png",
]

STYLE_FILES = [
    "neutrinohit-reveal.scss",
]


def copy_files(files: list[str], targets: list[Path]) -> None:
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        for name in files:
            source = SOURCE / name
            if not source.exists():
                raise FileNotFoundError(f"Missing shared asset: {source}")
            shutil.copy2(source, target / name)
            print(f"{source} -> {target / name}")


def main() -> None:
    copy_files(REVEAL_FILES, REVEAL_TARGETS)
    copy_files(STYLE_FILES, STYLE_TARGETS)


if __name__ == "__main__":
    main()
