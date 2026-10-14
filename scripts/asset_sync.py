"""Common engine for copying canonical shared assets into consumer repositories.

Used by sync_reveal_assets.py and sync_book_assets.py. Every consumer keeps a
local copy of the shared files so that it can be built on its own; this module
compares, reports and refreshes those copies.

Safety rules:
- only the repositories selected with --target or --all are touched (the
  documented legacy default is kept for scripts that ran without arguments);
- --check never writes and exits with status 1 when any copy differs;
- a destination file that has uncommitted changes in its repository
  (modified, staged or untracked) is not overwritten unless --force is given;
- a copy marked as held (the consumer must change its configuration first)
  is written only with --force;
- files that already match the canonical copy are not rewritten.
"""

from __future__ import annotations

import argparse
import difflib
import filecmp
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Copy:
    """One canonical file and the directory that receives it in a consumer."""

    source: str
    destination: str
    legacy: bool = False
    # Reason to keep the consumer copy for now. Reported by --check; the file
    # is written only with --force.
    hold: str = ""


@dataclass
class Consumer:
    repo: str
    copies: list[Copy] = field(default_factory=list)

    @property
    def root(self) -> Path:
        return WORKSPACE / self.repo


@dataclass
class Result:
    consumer: Consumer
    copy: Copy
    source: Path
    target: Path
    state: str  # same | differs | missing
    git_state: str = ""
    detail: str = ""


def git_status(repo_root: Path, path: Path) -> str | None:
    """Return the porcelain status of a path, "" when clean, None when unknown."""
    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        return None
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo_root), "status", "--porcelain", "--", str(relative)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[0][:2].strip() or "?"


def is_binary(path: Path) -> bool:
    return b"\0" in path.read_bytes()[:4096]


def change_summary(source: Path, target: Path) -> str:
    if is_binary(source) or is_binary(target):
        return f"binary, {target.stat().st_size} -> {source.stat().st_size} bytes"
    old = target.read_text(encoding="utf-8", errors="replace").splitlines()
    new = source.read_text(encoding="utf-8", errors="replace").splitlines()
    added = removed = 0
    for line in difflib.unified_diff(old, new, lineterm="", n=0):
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return f"sync would add {added} and remove {removed} lines"


def unified_diff(source: Path, target: Path) -> str:
    if is_binary(source) or is_binary(target):
        return ""
    old = target.read_text(encoding="utf-8", errors="replace").splitlines()
    new = source.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(
        difflib.unified_diff(old, new, fromfile=str(target), tofile=str(source), lineterm="")
    )


def compare(source_dir: Path, consumer: Consumer, copy: Copy) -> Result:
    source = source_dir / copy.source
    if not source.exists():
        raise FileNotFoundError(f"Missing shared asset: {source}")
    target = consumer.root / copy.destination / Path(copy.source).name
    if not target.exists():
        return Result(consumer, copy, source, target, "missing")
    if filecmp.cmp(source, target, shallow=False):
        state = "same"
    else:
        state = "differs"
    result = Result(consumer, copy, source, target, state)
    if state == "differs":
        status = git_status(consumer.root, target)
        result.git_state = "not a git checkout" if status is None else status
        result.detail = change_summary(source, target)
    return result


def extra_files(source_dir: Path, consumer: Consumer, known: set[str]) -> list[Path]:
    """Files named like shared assets that exist only in the consumer copy."""
    found: list[Path] = []
    for directory in sorted({copy.destination for copy in consumer.copies}):
        folder = consumer.root / directory
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name.startswith("neutrinohit-") and path.name not in known:
                if not (source_dir / path.name).exists():
                    found.append(path)
    return found


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def build_parser(description: str, epilog: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--target",
        action="append",
        metavar="REPO",
        help="consumer repository to process; repeat for several",
    )
    selection.add_argument("--all", action="store_true", help="process every consumer")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report differences only; exit 1 if any copy differs or is missing",
    )
    parser.add_argument(
        "--diff", action="store_true", help="with --check, print unified diffs of text files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite destination files even if they have uncommitted changes",
    )
    parser.add_argument("--list", action="store_true", help="list consumers and destinations")
    return parser


def select(
    consumers: list[Consumer], args: argparse.Namespace
) -> tuple[list[tuple[Consumer, list[Copy]]], bool]:
    """Return the (consumer, copies) pairs to process and whether legacy mode is used."""
    by_name = {consumer.repo: consumer for consumer in consumers}
    if args.target:
        unknown = [name for name in args.target if name not in by_name]
        if unknown:
            known = ", ".join(sorted(by_name))
            raise SystemExit(f"Unknown target(s): {', '.join(unknown)}. Known: {known}")
        names = list(dict.fromkeys(args.target))
        return [(by_name[name], by_name[name].copies) for name in names], False
    if args.all:
        return [(consumer, consumer.copies) for consumer in consumers], False
    legacy = []
    for consumer in consumers:
        copies = [copy for copy in consumer.copies if copy.legacy]
        if copies:
            legacy.append((consumer, copies))
    return legacy, True


def run(
    source_dir: Path,
    consumers: list[Consumer],
    args: argparse.Namespace,
    argv_name: str,
) -> int:
    if args.list:
        for consumer in consumers:
            print(consumer.repo)
            for copy in consumer.copies:
                flag = " (legacy default)" if copy.legacy else ""
                print(f"  {copy.source} -> {copy.destination}/{flag}")
        return 0

    selection, legacy = select(consumers, args)
    if legacy and not args.check:
        print(
            f"No target given: syncing the legacy default set. "
            f"Prefer `{argv_name} --target <repo>` or `--all`.",
            file=sys.stderr,
        )

    known = {copy.source for consumer in consumers for copy in consumer.copies}
    drift = 0
    refused = 0
    written = 0

    for consumer, copies in selection:
        print(f"[{consumer.repo}]")
        if not consumer.root.is_dir():
            print(f"  skipped: repository not found at {relative(consumer.root)}")
            drift += 1
            continue
        for copy in copies:
            result = compare(source_dir, consumer, copy)
            target = relative(result.target)
            if result.state == "same":
                print(f"  ok       {target}")
                continue

            if args.check:
                drift += 1
                if result.state == "missing":
                    print(f"  missing  {target}")
                else:
                    git_state = f" [local: {result.git_state}]" if result.git_state else ""
                    print(f"  differs  {target} ({result.detail}){git_state}")
                if copy.hold:
                    print(f"           held: {copy.hold}")
                if args.diff and result.state == "differs":
                    text = unified_diff(result.source, result.target)
                    if text:
                        print(text)
                continue

            if copy.hold and not args.force:
                refused += 1
                print(f"  held     {target}: {copy.hold}; use --force to write it")
                continue

            if result.state == "differs" and result.git_state and not args.force:
                refused += 1
                print(
                    f"  refused  {target}: uncommitted changes ({result.git_state}); "
                    f"commit or discard them, or use --force"
                )
                continue

            result.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result.source, result.target)
            written += 1
            print(f"  updated  {target}")

        if args.check:
            for path in extra_files(source_dir, consumer, known):
                print(f"  local    {relative(path)} (not in the canonical set)")

    if args.check:
        print(f"\n{drift} file(s) differ or are missing.")
        return 1 if drift else 0

    print(f"\n{written} file(s) updated, {refused} refused or held.")
    return 2 if refused else 0
