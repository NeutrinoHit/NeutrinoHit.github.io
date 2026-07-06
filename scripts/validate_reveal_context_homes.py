#!/usr/bin/env python3
from __future__ import annotations

import json
import errno
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
REGISTRY = ROOT / "scripts" / "reveal_context_targets.json"
CANONICAL_HOST = "neutrinohit.github.io"

SOURCE_ROOTS = [
    ROOT,
    WORKSPACE / "qft-lectures",
    WORKSPACE / "stat-course",
    WORKSPACE / "neutrinophysics",
    WORKSPACE / "particlephysics",
    WORKSPACE / "sciencepop",
    WORKSPACE / "talks",
]

SOURCE_SUFFIXES = {".qmd", ".yml", ".yaml", ".html"}
SITE_SUFFIXES = {".html"}

EXCLUDED_PARTS = {
    ".git",
    ".quarto",
    ".make-tmp",
    "_site",
    "pages",
    "node_modules",
    "assets/player",
    "pdf.worker.min.js",
}

READ_WARNINGS: list[str] = []
READ_WARNING_KEYS: set[str] = set()
REMOTE_TARGET_CACHE: dict[str, bool] = {}

SCRIPT_RE = re.compile(
    r"<script\b(?=[^>]*neutrinohit-reveal-footer\.js)(?P<attrs>[^>]*)>",
    re.IGNORECASE | re.DOTALL,
)
ATTR_RE = re.compile(
    r"(?P<name>[\w:-]+)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Occurrence:
    path: Path
    line: int
    attrs: dict[str, str]


def is_excluded(path: Path) -> bool:
    text = path.as_posix()
    parts = set(path.parts)
    if parts.intersection(EXCLUDED_PARTS):
        return True
    return "/assets/player/" in text or "/node_modules/" in text or "/.git/" in text


def iter_files(root: Path, suffixes: set[str], *, include_build: bool = False) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in suffixes
        and (include_build or not is_excluded(path))
    ]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        if getattr(exc, "errno", None) == errno.ETIMEDOUT or "Operation timed out" in str(exc):
            warn_once(f"dataless:{path}", f"skip unreadable dataless file: {rel(path)}")
            return ""
        raise


def warn_once(key: str, message: str) -> None:
    if key in READ_WARNING_KEYS:
        return
    READ_WARNING_KEYS.add(key)
    READ_WARNINGS.append(message)


def parse_attrs(raw_attrs: str) -> dict[str, str]:
    return {match.group("name").lower(): unescape(match.group("value").strip()) for match in ATTR_RE.finditer(raw_attrs)}


def find_occurrences(paths: list[Path]) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for path in paths:
        text = read_text(path)
        for match in SCRIPT_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            occurrences.append(Occurrence(path=path, line=line, attrs=parse_attrs(match.group("attrs"))))
    return occurrences


def load_allowed_targets() -> dict[str, str]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    targets = {entry["url"]: entry.get("type", "map-card") for entry in payload.get("allowed_context_homes", [])}
    if not targets:
        raise SystemExit("Reveal footer context registry is empty.")
    return targets


def page_for_url(url: str) -> tuple[Path, str] | None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != CANONICAL_HOST or not parsed.path:
        return None
    path = parsed.path.lstrip("/")
    if not path or parsed.path.endswith("/"):
        path = f"{path}index.html"
    return ROOT / "_site" / path, parsed.fragment


def target_anchor_exists(url: str) -> bool:
    target = page_for_url(url)
    if target is None:
        return False
    page, fragment = target
    if not page.exists():
        return False
    if not fragment:
        return True
    text = read_text(page)
    return re.search(rf"\bid\s*=\s*['\"]{re.escape(fragment)}['\"]", text) is not None


def target_page_exists(url: str) -> bool:
    target = page_for_url(url)
    return bool(target and target[0].exists())


def target_type_is_valid(url: str, target_type: str) -> bool:
    parsed = urlparse(url)
    if target_type == "map-card":
        return bool(parsed.fragment)
    if target_type == "course-home":
        return not parsed.fragment and parsed.path.endswith("/")
    return False


def remote_target_exists(url: str) -> bool:
    if url in REMOTE_TARGET_CACHE:
        return REMOTE_TARGET_CACHE[url]

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "NeutrinoHit reveal context validator"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            ok = 200 <= response.getcode() < 400
    except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError, OSError):
        ok = False

    REMOTE_TARGET_CACHE[url] = ok
    return ok


def target_exists_for_type(url: str, target_type: str) -> bool:
    if target_type == "course-home":
        return target_page_exists(url) or remote_target_exists(url)
    return target_anchor_exists(url)


def rel(path: Path) -> str:
    try:
        return path.relative_to(WORKSPACE).as_posix()
    except ValueError:
        return path.as_posix()


def validate_occurrence(occurrence: Occurrence, allowed_targets: dict[str, str]) -> list[str]:
    errors: list[str] = []
    home = occurrence.attrs.get("data-context-home", "").strip()
    label = occurrence.attrs.get("data-context-home-label", "").strip()

    if not home:
        errors.append("missing data-context-home")
    elif home not in allowed_targets:
        errors.append(f"data-context-home is not registered: {home}")
    elif not target_exists_for_type(home, allowed_targets[home]):
        errors.append(f"registered target page or anchor does not exist after render: {home}")

    if not label:
        errors.append("missing data-context-home-label")

    return errors


def main() -> int:
    allowed_targets = load_allowed_targets()

    source_files: list[Path] = []
    for root in SOURCE_ROOTS:
        source_files.extend(iter_files(root, SOURCE_SUFFIXES))

    site_files = iter_files(ROOT / "_site", SITE_SUFFIXES, include_build=True)
    occurrences = find_occurrences(source_files + site_files)

    errors: list[str] = []
    for url, target_type in sorted(allowed_targets.items()):
        if not target_type_is_valid(url, target_type):
            errors.append(f"registry target has invalid type/path combination: {url} ({target_type})")
        if not target_exists_for_type(url, target_type):
            errors.append(f"registry target page or anchor does not exist after render: {url}")

    for occurrence in occurrences:
        for message in validate_occurrence(occurrence, allowed_targets):
            errors.append(f"{rel(occurrence.path)}:{occurrence.line}: {message}")

    if errors:
        print("Reveal footer context validation failed.", file=sys.stderr)
        print(
            "Every presentation using neutrinohit-reveal-footer.js must define "
            "data-context-home and data-context-home-label. The home URL must be "
            "a registered absolute https://neutrinohit.github.io/... target from "
            "neutrinohit-map/scripts/reveal_context_targets.json. Map-card targets "
            "must include an anchor that exists in the rendered site. Course-home "
            "targets must exist either in the local preview copy or as published "
            "standalone course pages.",
            file=sys.stderr,
        )
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    for warning in READ_WARNINGS:
        print(f"[reveal-context] warning: {warning}")

    print(f"[reveal-context] validated {len(occurrences)} footer script tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
