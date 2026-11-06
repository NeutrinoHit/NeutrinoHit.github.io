#!/usr/bin/env python3
"""Shared films of NeutrinoHit: register, publish and check them (media.catalog.json).

  nh_media.py adopt [--dry-run]       register the films the main site serves now
                                      (gallery copies, own QR copies); stage them in .cache/media
  nh_media.py prepare FILE --id ID --variant V --home H [--version N] [--replaces [PROJECT:]PATH]...
                                      [--title-ru T] [--title-en T] [--credit TEXT]
                                      check and register one reviewed render
  nh_media.py project-add HOME --title T [--budget BYTES]
                                      add a media project to the catalog (a full one continues as <home>-2)
  nh_media.py rehome --id ID --variant V --version N --home H
                                      move a prepared record to another media project; a published
                                      record keeps its address and cannot be moved
  nh_media.py check                   validate the catalog, the staged copies and the budgets
  nh_media.py report                  bytes per media project and what the main site keeps
  nh_media.py project HOME [--out DIR]   write or refresh the media project (manifest, build, workflow)
  nh_media.py stage HOME --out DIR    build the media project's _site from .cache/media (local preview)
  nh_media.py publish HOME [--yes]    create the Releases and upload missing assets (dry run without --yes)
  nh_media.py verify HOME [--base URL] [--full] [--mark]
                                      check every address of the home on its Pages site; --mark sets
                                      the verified records to "published"
  nh_media.py prune-site SITE         delete from a built main site the copies replaced by live records
  nh_media.py replaced                tracked main-site copies that published films replace (for git rm)
  nh_media.py lock PROJECT_DIR        write media.lock.json of a consumer from its nh-video references
  nh_media.py extension PROJECT_DIR   copy the shared Quarto extension into a consumer
  nh_media.py guard-install REPO...   install the local pre-commit check against video files
  nh_media.py inventory [--json] [--check]
                                      every film: who makes it, where it is used; video files of the
                                      repositories outside the library (--check: exit 1 if any)

A film is identified by (id, variant, version); one SHA-256 is one record. Published
bytes never change: a new render gets a new version. See docs/media-library.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import media_registry as mr  # noqa: E402

SITE_ROOT = mr.SITE_ROOT
WORKSPACE = SITE_ROOT.parent
GALLERY = SITE_ROOT / "animations.catalog.json"
BOOKS = SITE_ROOT / "books.catalog.json"
EXTENSION = SITE_ROOT / "assets" / "media" / "_extensions" / "neutrinohit-media"
PROJECT_TEMPLATE = SITE_ROOT / "assets" / "media" / "project"
VIDEO_EXT = (".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi")
PAGES_LIMIT = 1_000_000_000
FOOTER_TAG = "dvn-footer-v1"

# gallery section -> media project; a QR copy goes by its book
# media-neutrino is full (6 November 2026): new films on neutrinos and particles go to media-neutrino-2
SECTION_HOME = {
    "neutrino-particles": "media-neutrino-2",
    "fields-waves": "media-qft",
    "relativity-atom-spin": "media-qft",
    "math-dynamical-systems": "media-mechanics",
    "accelerator-optics": "media-mechanics",
    "visual-stories": "media-mechanics",
}
BOOK_HOME = {"neutrino-physics": "media-neutrino-2", "particle-physics": "media-neutrino-2",
             "qft": "media-qft", "gravity": "media-qft"}


# ------------------------------------------------------------------ files

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height:format=duration:format_tags=comment",
         "-of", "json", str(path)], check=True, capture_output=True, text=True).stdout
    data = json.loads(out)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    if video is None:
        raise SystemExit(f"{path}: no video stream")
    return {
        "duration_s": round(float(data["format"].get("duration") or 0.0), 2),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "video_codec": video["codec_name"],
        "audio": any(s.get("codec_type") == "audio" for s in data["streams"]),
        "footer": data["format"].get("tags", {}).get("comment", "") == FOOTER_TAG,
    }


def faststart(path: Path) -> bool:
    """True when the moov atom comes before mdat (the browser can start and seek at once)."""
    with path.open("rb") as handle:
        while True:
            head = handle.read(8)
            if len(head) < 8:
                return False
            size, kind = int.from_bytes(head[:4], "big"), head[4:]
            if kind == b"moov":
                return True
            if kind == b"mdat":
                return False
            if size == 1:
                size = int.from_bytes(handle.read(8), "big")
                handle.seek(size - 16, 1)
            elif size == 0:
                return False
            else:
                handle.seek(size - 8, 1)


def stage(path: Path, digest: str, ext: str = "mp4") -> Path:
    """Copy into the content-addressed cache (an APFS clone costs no space)."""
    mr.CACHE.mkdir(parents=True, exist_ok=True)
    target = mr.CACHE / f"{digest}.{ext}"
    if not target.exists():
        tmp = target.with_suffix(".tmp")
        if subprocess.run(["cp", "-c", str(path), str(tmp)], capture_output=True).returncode != 0:
            shutil.copyfile(path, tmp)
        tmp.replace(target)
    return target


DOCUMENT_EXT = ("pdf", "zip", "csv", "json", "npz", "txt", "gz")
CONTENT_TYPE = {"mp4": "video/mp4", "pdf": "application/pdf", "zip": "application/zip", "csv": "text/csv",
                "json": "application/json", "npz": "application/octet-stream", "txt": "text/plain",
                "gz": "application/gzip"}


def is_video(record_or_path: dict[str, Any] | Path) -> bool:
    ext = record_or_path.suffix.lower().lstrip(".") if isinstance(record_or_path, Path) \
        else mr.ext_of(record_or_path)
    return ext in ("mp4", "m4v", "mov", "webm")


def describe(path: Path) -> dict[str, Any]:
    if not is_video(path):
        ext = path.suffix.lower().lstrip(".")
        if ext not in DOCUMENT_EXT:
            raise SystemExit(f"{path}: unsupported file type .{ext} (films: mp4; documents: {', '.join(DOCUMENT_EXT)})")
        return {"sha256": sha256(path), "bytes": path.stat().st_size, "ext": ext}
    info = probe(path)
    return {"sha256": sha256(path), "bytes": path.stat().st_size, **info, "faststart": faststart(path)}


# ---------------------------------------------------------------- catalog

def find_sha(catalog: dict[str, Any], digest: str) -> dict[str, Any] | None:
    return next((r for r in catalog["media"] if r["sha256"] == digest), None)


def find_key(catalog: dict[str, Any], ident: str, variant: str, version: int) -> dict[str, Any] | None:
    return next((r for r in catalog["media"]
                 if (r["id"], r["variant"], r["version"]) == (ident, variant, version)), None)


def add(catalog: dict[str, Any], path: Path, ident: str, variant: str, home: str, replaces: list[str],
        version: int = 1, title: dict[str, str] | None = None, credit: str = "",
        info: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Register one file; returns ("new" | "same" | "merged", record)."""
    if home not in catalog["projects"]:
        raise SystemExit(f"unknown media project {home}; known: {', '.join(catalog['projects'])}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", ident) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", variant):
        raise SystemExit(f"id and variant are lower-case words with hyphens: {ident} {variant}")
    info = info or describe(path)
    same = find_sha(catalog, info["sha256"])
    if same:
        new = [p for p in replaces if p not in same["replaces"]]
        same["replaces"] += new
        return ("merged" if new else "same"), same
    if find_key(catalog, ident, variant, version):
        raise SystemExit(f"{ident}/{variant}/v{version} exists with other bytes: give a new --version")
    record = {"id": ident, "variant": variant, "version": version, "home": home, "status": "prepared",
              **info, "replaces": list(replaces)}
    if title:
        record["title"] = title
    if credit:
        record["credit"] = credit
    catalog["media"].append(record)
    return "new", record


def add_project(catalog: dict[str, Any], home: str, title: str, budget: int = 900_000_000) -> dict[str, Any]:
    """A new media project in the catalog: the address /<home>/ of its own Pages site."""
    if not re.fullmatch(r"media-[a-z0-9][a-z0-9-]*", home):
        raise SystemExit(f"a media project is named media-<words>: {home}")
    if home in catalog["projects"]:
        raise SystemExit(f"{home} is already in the catalog")
    if not 0 < budget < PAGES_LIMIT:
        raise SystemExit(f"budget must stay under the Pages limit of {PAGES_LIMIT} bytes")
    catalog["projects"][home] = {"title": title, "budget_bytes": budget}
    return catalog["projects"][home]


def rehome(catalog: dict[str, Any], ident: str, variant: str, version: int, home: str) -> tuple[str, dict[str, Any]]:
    """Move a prepared record to another media project; returns ("moved" | "same", record).

    Only a prepared record moves: a published one is served at /<home>/... and published
    addresses never change (register the film again as a new version instead).
    """
    record = find_key(catalog, ident, variant, version)
    if not record:
        raise SystemExit(f"{ident}/{variant}/v{version} is not in the catalog")
    if home not in catalog["projects"]:
        raise SystemExit(f"unknown media project {home}; add it first (nh_media.py project-add)")
    if record["home"] == home:
        return "same", record
    if record.get("status") != "prepared":
        raise SystemExit(f"{mr.key(record)} is published at {mr.url_of(record, catalog)}: "
                         f"its address cannot change; register a new version in {home}")
    total = sum(r["bytes"] for r in catalog["media"] if r["home"] == home) + record["bytes"]
    if total > catalog["projects"][home]["budget_bytes"]:
        raise SystemExit(f"{home}: {total} bytes would exceed its budget {catalog['projects'][home]['budget_bytes']}")
    record["home"] = home
    return "moved", record


def gallery_variant(item: dict[str, Any], video: dict[str, Any]) -> str:
    """web[-<film>][-<lang>]: the variant of a gallery copy, from its video id and language label."""
    vid, iid = video["id"], item["id"]
    base = vid[len(iid):].strip("-") if vid.startswith(iid) else vid
    lang = ""
    label = video.get("label", "")
    if "English version" in label:
        lang = "en"
    elif "русская версия" in label or label.startswith("Русская версия"):
        lang = "ru"
    for code in ("en", "ru"):
        if base == code or base.endswith("-" + code):
            base, lang = base[: -len(code)].rstrip("-"), code
    return "-".join(["web"] + ([base] if base else []) + ([lang] if lang else []))


def cmd_adopt(args: argparse.Namespace) -> int:
    catalog = mr.load()
    gallery = json.loads(GALLERY.read_text(encoding="utf-8"))
    plan: list[tuple[Path, str, str, str, str, dict[str, str]]] = []
    for section in gallery["sections"]:
        home = SECTION_HOME[section["id"]]
        for item in section["items"]:
            for video in item["videos"]:
                if video.get("publish_with_project_site"):
                    continue
                rel = f'assets/animations/dvnanima/{section["id"]}-{item["id"]}-{video["id"]}.mp4'
                title = {"ru": item["title"], "en": item.get("title_en") or item["title"]}
                plan.append((SITE_ROOT / rel, item["id"], gallery_variant(item, video), home, rel, title))
    registry = json.loads(BOOKS.read_text(encoding="utf-8"))
    for book in registry["books"]:
        if book.get("status", "published") != "published":
            continue
        for item in json.loads((SITE_ROOT / book["catalog"]).read_text(encoding="utf-8"))["items"]:
            media = item.get("media", {})
            if item["hosting"] != "self" or media.get("site_asset"):
                continue
            rel = f'assets/{book["asset_subdir"]}/{item["id"]}.mp4'
            plan.append((SITE_ROOT / rel, item["slug"], f'qr-{book["slug"]}', BOOK_HOME[book["slug"]], rel,
                         item["title"]))
    counts = {"new": 0, "same": 0, "merged": 0, "missing": 0}
    seen: set[tuple[str, str]] = set()
    for path, ident, variant, home, rel, title in plan:
        if (ident, variant) in seen:
            raise SystemExit(f"two site copies map to {ident}/{variant}: {rel}")
        seen.add((ident, variant))
        if not path.is_file():
            counts["missing"] += 1
            print(f"missing: {rel}")
            continue
        info = describe(path)
        state, record = add(catalog, path, ident, variant, home, [rel], title=title, info=info)
        counts[state] += 1
        if state == "new" and not args.dry_run:
            stage(path, info["sha256"])
    if not args.dry_run:
        mr.save(catalog)
    print(", ".join(f"{k}: {v}" for k, v in counts.items()) + ("  (dry run)" if args.dry_run else ""))
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    catalog = mr.load()
    info = describe(path)
    problems = []
    video = "video_codec" in info
    if video and info["video_codec"] != "h264":
        problems.append(f"codec {info['video_codec']} (browsers need h264)")
    if video and not info["faststart"]:
        problems.append("moov atom after mdat: re-mux with -movflags +faststart")
    if problems and not args.force:
        raise SystemExit("not ready: " + "; ".join(problems))
    if video and not info["footer"]:
        print(f"note: no footer tag {FOOTER_TAG} (films of dvnanima carry it; others may not)")
    title = {k: v for k, v in (("ru", args.title_ru), ("en", args.title_en)) if v}
    state, record = add(catalog, path, args.id, args.variant, args.home, args.replaces or [],
                        version=args.version, title=title or None, credit=args.credit or "", info=info)
    if state == "new":
        stage(path, info["sha256"], mr.ext_of(record))
    mr.save(catalog)
    detail = (f"  audio={'yes' if record['audio'] else 'no'}  {record['width']}x{record['height']}"
              f"  {record['duration_s']} s") if is_video(record) else f"  {mr.ext_of(record)}"
    print(f"{state}: {mr.key(record)}  {mr.human_bytes(record['bytes'])}  {mr.url_of(record, catalog)}{detail}")
    if state != "new":
        print("identical bytes are already registered: no new file")
    return 0


def cmd_project_add(args: argparse.Namespace) -> int:
    catalog = mr.load()
    add_project(catalog, args.home, args.title, args.budget)
    mr.save(catalog)
    print(f"added: {args.home} ({args.title}), budget {args.budget} bytes; next: nh_media.py project {args.home}")
    return 0


def cmd_rehome(args: argparse.Namespace) -> int:
    catalog = mr.load()
    old = (find_key(catalog, args.id, args.variant, args.version) or {}).get("home")
    state, record = rehome(catalog, args.id, args.variant, args.version, args.home)
    mr.save(catalog)
    print(f"{state}: {mr.key(record)} {old} -> {record['home']}  {mr.url_of(record, catalog)}")
    if state == "moved":
        print(f"refresh both manifests: nh_media.py project {old}; nh_media.py project {record['home']}")
    return 0


def check(catalog: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    keys: set[tuple] = set()
    hashes: set[str] = set()
    paths: dict[str, str] = {}
    for record in catalog["media"]:
        k = (record["id"], record["variant"], record["version"])
        if k in keys:
            problems.append(f"{mr.key(record)}: duplicate id/variant/version")
        keys.add(k)
        if record["sha256"] in hashes:
            problems.append(f"{mr.key(record)}: the same bytes are registered twice")
        hashes.add(record["sha256"])
        if record.get("status") not in mr.STATUSES:
            problems.append(f"{mr.key(record)}: status must be one of {mr.STATUSES}")
        if record["home"] not in catalog["projects"]:
            problems.append(f"{mr.key(record)}: unknown home {record['home']}")
        if record.get("status") == "prepared" and not mr.cached(record).is_file():
            problems.append(f"{mr.key(record)}: prepared but not staged in .cache/media")
        if is_video(record) and record.get("video_codec") != "h264":
            problems.append(f"{mr.key(record)}: codec {record.get('video_codec')}")
        for path in record.get("replaces", []):
            if path.startswith("/") or "/Users/" in path or ".." in path.split("/"):
                problems.append(f"{mr.key(record)}: replaces must be a relative site path: {path}")
            if path in paths:
                problems.append(f"{path}: replaced by {paths[path]} and {mr.key(record)}")
            paths[path] = mr.key(record)
            local = SITE_ROOT / path
            if ":" not in path and record.get("status") != "published" and not local.is_file():
                problems.append(f"{mr.key(record)}: {path} is gone while the record is not published")
        text = json.dumps(record)
        if re.search(r"github\.com/[^/\"]+/dvnanima|/Users/|/private/", text):
            problems.append(f"{mr.key(record)}: private paths do not belong in the public catalog")
    for home, project in catalog["projects"].items():
        total = sum(r["bytes"] for r in catalog["media"] if r["home"] == home)
        if total > project["budget_bytes"]:
            problems.append(f"{home}: {total} bytes over the budget {project['budget_bytes']}")
    return problems


def cmd_check(_: argparse.Namespace) -> int:
    catalog = mr.load()
    problems = check(catalog)
    for problem in problems:
        print("  -", problem)
    print(f"{'FAIL' if problems else 'OK'}: {len(catalog['media'])} films, {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_report(_: argparse.Namespace) -> int:
    catalog = mr.load()
    for home, project in catalog["projects"].items():
        records = [r for r in catalog["media"] if r["home"] == home]
        total = sum(r["bytes"] for r in records)
        published = sum(1 for r in records if r["status"] == "published")
        print(f"{home:16} {len(records):4} films  {total / 1e6:7.1f} MB of {project['budget_bytes'] / 1e6:.0f} MB"
              f"  ({100 * total / PAGES_LIMIT:.0f}% of 1 GB)  published {published}/{len(records)}")
    replaced = {p for r in catalog["media"] for p in r["replaces"] if ":" not in p}
    present = [SITE_ROOT / p for p in replaced if (SITE_ROOT / p).is_file()]
    print(f"main site copies registered: {len(replaced)} ({sum(p.stat().st_size for p in present) / 1e6:.1f} MB on disk)")
    return 0


# --------------------------------------------------------- media projects

def records_of(catalog: dict[str, Any], home: str, ident: str | None = None) -> list[dict[str, Any]]:
    if home not in catalog["projects"]:
        raise SystemExit(f"unknown media project {home}")
    records = [r for r in catalog["media"] if r["home"] == home and (ident is None or r['id'] == ident)]
    if ident is not None and not records:
        raise SystemExit(f"unknown story {ident} in {home}")
    return records


def manifest(catalog: dict[str, Any], home: str) -> dict[str, Any]:
    project = catalog["projects"][home]
    return {
        "schema": 1,
        "home": home,
        "title": project["title"],
        "budget_bytes": project["budget_bytes"],
        "media": [{
            "id": r["id"], "variant": r["variant"], "version": r["version"],
            "file": mr.file_of(r), "asset": mr.asset_name(r), "release": r["id"],
            "url": mr.release_url(r, catalog), "sha256": r["sha256"], "bytes": r["bytes"],
            **({"duration_s": r["duration_s"], "width": r["width"], "height": r["height"], "audio": r["audio"]}
               if is_video(r) else {"type": mr.ext_of(r)}),
            **({"title": r["title"]} if r.get("title") else {}),
            **({"credit": r["credit"]} if r.get("credit") else {}),
        } for r in records_of(catalog, home)],
    }


def cmd_project(args: argparse.Namespace) -> int:
    catalog = mr.load()
    out = Path(args.out or WORKSPACE / args.home).resolve()
    out.mkdir(parents=True, exist_ok=True)
    project = catalog["projects"][args.home]
    for source in sorted(PROJECT_TEMPLATE.rglob("*")):
        if source.is_dir() or "__pycache__" in source.parts:
            continue
        target = out / source.relative_to(PROJECT_TEMPLATE)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        text = text.replace("@HOME@", args.home).replace("@TITLE@", project["title"])
        target.write_text(text, encoding="utf-8")
    (out / "media.manifest.json").write_text(
        json.dumps(manifest(catalog, args.home), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{args.home}: {len(records_of(catalog, args.home))} films -> {out}")
    return 0


def cmd_stage(args: argparse.Namespace) -> int:
    root = WORKSPACE / args.home
    command = [sys.executable, str(root / "scripts" / "build_site.py"), "--from-cache", str(mr.CACHE),
               "--out", str(Path(args.out).resolve())]
    return subprocess.run(command, cwd=root).returncode


def gh(*command: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *command], capture_output=True, text=True, check=check)


def cmd_publish(args: argparse.Namespace) -> int:
    catalog = mr.load()
    repo = f'{catalog["github"]}/{args.home}'
    records = records_of(catalog, args.home, getattr(args, 'id', None))
    if args.yes and gh("repo", "view", repo, "--json", "name", check=False).returncode != 0:
        raise SystemExit(f"{repo} does not exist on GitHub yet (see docs/media-library.md, first publication)")
    releases: dict[str, dict[str, Any]] = {}
    todo = 0
    for record in records:
        tag = record["id"]
        if tag not in releases:
            got = gh("api", f"repos/{repo}/releases/tags/{tag}", check=False) if args.yes or args.online else None
            releases[tag] = json.loads(got.stdout) if got and got.returncode == 0 else {}
        assets = {a["name"]: a for a in releases[tag].get("assets", [])}
        name = mr.asset_name(record)
        if name in assets:
            have = assets[name]
            digest = (have.get("digest") or "").removeprefix("sha256:")
            if have["size"] != record["bytes"] or (digest and digest != record["sha256"]):
                raise SystemExit(f"{tag}/{name} is published with other bytes: never overwritten; "
                                 "register the new render as a new version")
            continue
        todo += 1
        print(f"{'upload' if args.yes else 'would upload'}: {tag}/{name}  {mr.human_bytes(record['bytes'])}")
        if not args.yes:
            continue
        if not releases[tag]:
            title = (record.get("title") or {}).get("en") or tag
            gh("release", "create", tag, "-R", repo, "--title", title, "--notes",
               f"Published films of the story {tag}. Files are immutable; a new render is a new version.")
            releases[tag] = {"assets": []}
        source = mr.cached(record)
        if not source.is_file() or sha256(source) != record["sha256"]:
            raise SystemExit(f"{source}: staged copy missing or changed")
        with tempfile.TemporaryDirectory() as tmp:
            named = Path(tmp) / name
            if subprocess.run(["cp", "-c", str(source), str(named)], capture_output=True).returncode != 0:
                shutil.copyfile(source, named)
            gh("release", "upload", tag, str(named), "-R", repo)
        releases[tag]["assets"].append({"name": name, "size": record["bytes"]})
    print(f"{args.home}: {todo} asset(s) {'uploaded' if args.yes else 'to upload (dry run; add --yes)'}")
    return 0


def http_range(url: str, first: int, last: int) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, headers={"Range": f"bytes={first}-{last}"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), b""


def cmd_verify(args: argparse.Namespace) -> int:
    catalog = mr.load()
    base = args.base.rstrip("/")
    bad = 0
    verified = []
    for record in records_of(catalog, args.home, getattr(args, 'id', None)):
        url = base + mr.url_of(record, catalog)
        status, headers, head = http_range(url, 0, 1023)
        total = (headers.get("Content-Range") or "").rpartition("/")[2]
        kind = headers.get("Content-Type", "")
        small = record["bytes"] <= 1024           # served whole: 200 without Content-Range
        expected = CONTENT_TYPE.get(mr.ext_of(record), "application/")
        typed = kind.startswith(expected) or (mr.ext_of(record) == "zip" and "zip" in kind)
        ok = typed and ((status == 206 and total == str(record["bytes"]))
                        or (small and status in (200, 206) and len(head) == record["bytes"]))
        if ok and not small:
            status, _, tail = http_range(url, record["bytes"] - 1024, record["bytes"] - 1)
            ok = status == 206 and len(tail) == 1024
        if ok and args.full:
            with urllib.request.urlopen(url, timeout=600) as response:
                ok = hashlib.sha256(response.read()).hexdigest() == record["sha256"]
        print(f"{'ok ' if ok else 'BAD'} {url}" + ("" if ok else f"  (HTTP {status}, {kind}, size {total})"))
        bad += not ok
        if ok:
            verified.append(record)
    if args.mark and verified:
        for record in verified:
            record["status"] = "published"
        mr.save(catalog)
        print(f"marked published: {len(verified)}")
    return 1 if bad else 0


# ------------------------------------------------------------ consumers

def cmd_prune_site(args: argparse.Namespace) -> int:
    site = Path(args.site)
    removed = freed = 0
    for path in sorted(mr.Resolver().replaced()):
        target = site / path
        if target.is_file():
            freed += target.stat().st_size
            target.unlink()
            removed += 1
    left = [p for p in site.rglob("*") if p.suffix.lower() in VIDEO_EXT and p.is_file()]
    print(f"shared media: removed {removed} copies ({freed / 1e6:.1f} MB); "
          f"videos left in the site: {len(left)} ({sum(p.stat().st_size for p in left) / 1e6:.1f} MB)")
    return 0


def cmd_replaced(_: argparse.Namespace) -> int:
    """Tracked copies of the main site that published films replace: input for `git rm`."""
    tracked = set(subprocess.run(["git", "-C", str(SITE_ROOT), "ls-files", "-z"], capture_output=True,
                                 text=True, check=True).stdout.split("\0"))
    for path in sorted(mr.Resolver().replaced() & tracked):
        print(path)
    return 0


REFERENCE = re.compile(r'\{\{<\s*nh-(?:video|url)\s+([a-z0-9-]+)\s+[^>]*?variant="([a-z0-9-]+)"'
                       r'|nh:([a-z0-9-]+)/([a-z0-9-]+)')


def cmd_lock(args: argparse.Namespace) -> int:
    root = Path(args.project).resolve()
    catalog = mr.load()
    lock_path = root / "media.lock.json"
    old = {(e["id"], e["variant"]): e for e in
           (json.loads(lock_path.read_text())["media"] if lock_path.is_file() else [])}
    refs: set[tuple[str, str]] = set()
    for qmd in root.rglob("*.qmd"):
        if {"_site", ".quarto", "_extensions", ".work"} & set(qmd.relative_to(root).parts):
            continue
        for m in REFERENCE.finditer(qmd.read_text(encoding="utf-8")):
            refs.add((m.group(1) or m.group(3), m.group(2) or m.group(4)))
    entries, problems = [], []
    for ident, variant in sorted(refs):
        versions = [r for r in catalog["media"] if (r["id"], r["variant"]) == (ident, variant)]
        if not versions:
            problems.append(f"{ident}/{variant}: not in media.catalog.json")
            continue
        pinned = old.get((ident, variant), {}).get("version") or max(r["version"] for r in versions)
        record = next((r for r in versions if r["version"] == pinned), None)
        if record is None:
            problems.append(f"{ident}/{variant}: pinned version {pinned} is not in the catalog")
            continue
        newer = max(r["version"] for r in versions)
        if newer > pinned:
            print(f"note: {ident}/{variant} is pinned to v{pinned}; v{newer} exists (update the lock deliberately)")
        prefix = root.name + ":"
        fallback = next((p[len(prefix):] for p in record["replaces"] if p.startswith(prefix)), "")
        entries.append({"id": ident, "variant": variant, "version": pinned,
                        "url": mr.url_of(record, catalog), "sha256": record["sha256"],
                        "bytes": record["bytes"], "status": record["status"],
                        **({"fallback": fallback} if fallback else {})})
    if problems:
        raise SystemExit("\n".join(problems))
    lock_path.write_text(json.dumps({"schema": 1, "generated_by": "neutrinohit-map/scripts/nh_media.py lock",
                                     "media": entries}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{lock_path}: {len(entries)} film(s)")
    return 0


def cmd_extension(args: argparse.Namespace) -> int:
    target = Path(args.project).resolve() / "_extensions" / "neutrinohit-media"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(EXTENSION, target, ignore=shutil.ignore_patterns("__pycache__"))
    print(f"extension -> {target}")
    return 0


HOOK_MARK = "# neutrinohit-media-guard"
HOOK = (Path(__file__).resolve().parent / "media_guard.sh").read_text(encoding="utf-8")


def cmd_guard_install(args: argparse.Namespace) -> int:
    for repo in args.repos:
        hooks = subprocess.run(["git", "-C", repo, "rev-parse", "--git-path", "hooks"], capture_output=True,
                               text=True, check=True).stdout.strip()   # honours core.hooksPath
        hook = (Path(repo) / hooks if not os.path.isabs(hooks) else Path(hooks)) / "pre-commit"
        if hook.exists() and HOOK_MARK not in hook.read_text(errors="replace"):
            print(f"{repo}: a different pre-commit hook exists; left as is")
            continue
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(HOOK, encoding="utf-8")
        hook.chmod(0o755)
        print(f"{repo}: guard installed")
    return 0


def cmd_inventory(args: argparse.Namespace) -> int:
    import media_inventory
    data = media_inventory.build()
    found = media_inventory.problems(data)
    if args.json:
        data["problems"] = found
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        states: dict[str, int] = {}
        for entry in data["repo_files"]:
            states[entry["state"]] = states.get(entry["state"], 0) + 1
        makers: dict[str, int] = {}
        for film in data["films"]:
            makers[film["maker"]["kind"]] = makers.get(film["maker"]["kind"], 0) + 1
        unused = sum(1 for film in data["films"] if not film["uses"])
        print(f"films: {len(data['films'])} (makers: {makers}; without a known use: {unused})")
        print(f"video files in repositories: {states}")
        print(f"dvnanima renders not in the library: {len(data['dvnanima_unpublished'])}")
        for line in found:
            print("  -", line)
    return 1 if args.check and found else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("adopt")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("prepare")
    p.add_argument("file")
    p.add_argument("--id", required=True)
    p.add_argument("--variant", required=True)
    p.add_argument("--home", required=True)
    p.add_argument("--version", type=int, default=1)
    p.add_argument("--replaces", action="append")
    p.add_argument("--title-ru")
    p.add_argument("--title-en")
    p.add_argument("--credit")
    p.add_argument("--force", action="store_true", help="register although codec/faststart checks fail")
    p = sub.add_parser("project-add")
    p.add_argument("home")
    p.add_argument("--title", required=True)
    p.add_argument("--budget", type=int, default=900_000_000)
    p = sub.add_parser("rehome")
    p.add_argument("--id", required=True)
    p.add_argument("--variant", required=True)
    p.add_argument("--version", type=int, required=True)
    p.add_argument("--home", required=True)
    sub.add_parser("check")
    sub.add_parser("report")
    p = sub.add_parser("project")
    p.add_argument("home")
    p.add_argument("--out")
    p = sub.add_parser("stage")
    p.add_argument("home")
    p.add_argument("--out", required=True)
    p = sub.add_parser("publish")
    p.add_argument("home")
    p.add_argument("--id", help="publish only this story, leaving other prepared stories untouched")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--online", action="store_true", help="dry run that also asks GitHub what exists")
    p = sub.add_parser("verify")
    p.add_argument("home")
    p.add_argument("--id", help="verify and optionally mark only this story")
    p.add_argument("--base", default="https://neutrinohit.github.io")
    p.add_argument("--full", action="store_true", help="download every film and compare SHA-256")
    p.add_argument("--mark", action="store_true")
    p = sub.add_parser("prune-site")
    p.add_argument("site")
    sub.add_parser("replaced")
    p = sub.add_parser("lock")
    p.add_argument("project")
    p = sub.add_parser("inventory")
    p.add_argument("--json", action="store_true")
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("extension")
    p.add_argument("project")
    p = sub.add_parser("guard-install")
    p.add_argument("repos", nargs="+")
    args = parser.parse_args()
    handler = {"adopt": cmd_adopt, "prepare": cmd_prepare, "project-add": cmd_project_add, "rehome": cmd_rehome,
               "check": cmd_check, "report": cmd_report,
               "project": cmd_project, "stage": cmd_stage, "publish": cmd_publish, "verify": cmd_verify,
               "prune-site": cmd_prune_site, "replaced": cmd_replaced, "lock": cmd_lock, "extension": cmd_extension, "inventory": cmd_inventory,
               "guard-install": cmd_guard_install}[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
