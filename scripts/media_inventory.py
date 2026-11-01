"""Inventory of all films of NeutrinoHit: who makes each one, where it is used, what is not registered.

Read-only over the workspace: the shared catalog, media.lock.json and nh-video references of the
consumer repositories, tracked video files of every registered repository, and the renders of
dvnanima. SHA-256 of local files are cached in .cache/media-inventory.json by (size, mtime).
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import media_registry as mr

SITE_ROOT = mr.SITE_ROOT
WORKSPACE = SITE_ROOT.parent
REGISTRY = WORKSPACE / ".neutrinohit" / "PROJECTS.md"
KEPT = SITE_ROOT / "media.kept.json"
HASH_CACHE = SITE_ROOT / ".cache" / "media-inventory.json"
PRODUCER = "dvnanima"
VIDEO = re.compile(r"\.(mp4|m4v|mov|webm|mkv|avi)$", re.I)
TEXT = re.compile(r"\.(qmd|md|html|htm|yml|yaml|json|js|lua|tex|py)$", re.I)
SKIP_PARTS = {"_site", ".quarto", ".work", ".cache", "node_modules", "partial_movie_files"}
REFERENCE = re.compile(r'\{\{<\s*nh-(?:video|url)\s+([a-z0-9-]+)\s+[^>]*?variant="([a-z0-9-]+)"'
                       r'|nh:([a-z0-9-]+)/([a-z0-9-]+)')
SCAN_KINDS = {"site"}             # published repositories; private manuscripts and the book keep their media


def registry() -> list[tuple[str, str]]:
    """(folder, kind) of every registered top-level entry."""
    rows = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] not in ("Folder", "---") and not cells[0].startswith("-"):
            rows.append((cells[0], cells[1]))
    return rows


class Hashes:
    def __init__(self) -> None:
        try:
            self.data = json.loads(HASH_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}
        self.dirty = False

    def of(self, path: Path) -> str:
        stat = path.stat()
        key = str(path)
        mark = [stat.st_size, int(stat.st_mtime)]
        hit = self.data.get(key)
        if hit and hit[:2] == mark:
            return hit[2]
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        self.data[key] = [*mark, digest.hexdigest()]
        self.dirty = True
        return digest.hexdigest()

    def save(self) -> None:
        if self.dirty:
            HASH_CACHE.parent.mkdir(parents=True, exist_ok=True)
            HASH_CACHE.write_text(json.dumps(self.data), encoding="utf-8")


def tracked(repo: Path) -> list[str]:
    done = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, text=True)
    if done.returncode != 0:
        return []
    return [p for p in done.stdout.split("\0") if p and not SKIP_PARTS & set(Path(p).parts)]


def dvnanima_renders(hashes: Hashes) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """sha256 -> scene/file for every render of dvnanima; final renders are <scene>/media/*.mp4."""
    root = WORKSPACE / PRODUCER
    by_sha: dict[str, str] = {}
    finals: list[dict[str, Any]] = []
    if not root.is_dir():
        return by_sha, finals
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not VIDEO.search(path.name) or SKIP_PARTS & set(rel.parts) or ".git" in rel.parts \
                or not path.is_file():
            continue
        try:
            sha = hashes.of(path)
        except OSError:           # an evicted cloud copy or an unreadable file: skip it
            continue
        by_sha.setdefault(sha, str(rel))
        if len(rel.parts) == 3 and rel.parts[1] == "media":
            finals.append({"scene": rel.parts[0], "file": str(rel), "sha256": sha, "bytes": path.stat().st_size})
    return by_sha, finals


def maker_of(record: dict[str, Any], renders: dict[str, str], scenes: dict[str, str]) -> dict[str, str]:
    if record.get("source"):
        return {"kind": "explicit", "source": record["source"]}
    if record["sha256"] in renders:
        path = renders[record["sha256"]]
        return {"kind": PRODUCER, "scene": path.split("/")[0], "file": path}
    scene = scenes.get(re.sub(r"[^a-z0-9]", "", record["id"].lower()))
    if scene:
        return {"kind": PRODUCER, "scene": scene, "match": "name"}
    if record.get("footer"):
        return {"kind": PRODUCER, "match": "footer"}
    if record.get("credit"):
        return {"kind": "other", "source": record["credit"]}
    return {"kind": "unknown"}


def map_use(path: str) -> dict[str, str]:
    if path.startswith("assets/animations/"):
        return {"project": "neutrinohit-map", "where": "gallery", "file": path}
    if path.startswith("assets/book-animations/") or path.startswith("assets/"):
        part = path.split("/")
        return {"project": "neutrinohit-map", "where": f"QR {part[2] if len(part) > 2 else ''}".strip(),
                "file": path}
    return {"project": "neutrinohit-map", "where": "site", "file": path}


def build() -> dict[str, Any]:
    catalog = mr.load()
    hashes = Hashes()
    renders, finals = dvnanima_renders(hashes)
    root = WORKSPACE / PRODUCER
    scene_dirs = [str(p.relative_to(root)) for p in [*root.glob("*"), *root.glob("*/*")]
                  if p.is_dir() and not p.name.startswith((".", "_")) and p.name not in ("media", "videos")] \
        if root.is_dir() else []
    scenes = {re.sub(r"[^a-z0-9]", "", name.split("/")[-1].lower()): name for name in reversed(scene_dirs)}
    kept = {k["path"]: k["reason"] for k in
            (json.loads(KEPT.read_text(encoding="utf-8"))["kept"] if KEPT.is_file() else [])}
    by_sha = {r["sha256"]: r for r in catalog["media"]}
    by_path = {p: r for r in catalog["media"] for p in r["replaces"]}
    film_of: dict[str, dict[str, Any]] = {}
    by_key = {(r["id"], r["variant"]): [] for r in catalog["media"]}
    films = []
    for record in catalog["media"]:
        uses = [map_use(p) for p in record["replaces"] if ":" not in p]
        films.append({
            "id": record["id"], "variant": record["variant"], "version": record["version"],
            "home": record["home"], "status": record["status"], "title": record.get("title", {}),
            "bytes": record["bytes"], "duration_s": record.get("duration_s"), "audio": record.get("audio"), "type": mr.ext_of(record),
            "url": "https://neutrinohit.github.io" + mr.url_of(record, catalog),
            "maker": maker_of(record, renders, scenes), "uses": uses,
            "replaced": [p for p in record["replaces"]],
        })
        by_key[(record["id"], record["variant"])].append(films[-1])
        film_of[mr.key(record)] = films[-1]

    files: list[dict[str, Any]] = []
    for folder, kind in registry():
        repo = WORKSPACE / folder
        if kind not in SCAN_KINDS or folder == PRODUCER or folder.startswith("media-") \
                or not (repo / ".git").exists():
            continue
        paths = tracked(repo)
        texts = {}
        for rel in paths:
            if TEXT.search(rel) and (repo / rel).is_file():
                try:
                    texts[rel] = (repo / rel).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    pass
        for rel, text in texts.items():
            if not rel.endswith(".qmd"):
                continue
            for m in REFERENCE.finditer(text):
                key = (m.group(1) or m.group(3), m.group(2) or m.group(4))
                for film in by_key.get(key, []):
                    use = {"project": folder, "where": "page", "file": rel}
                    if use not in film["uses"]:
                        film["uses"].append(use)
        for rel in paths:
            path = repo / rel
            if not VIDEO.search(rel) or not path.is_file():
                continue
            try:
                sha = hashes.of(path)
            except OSError:
                sha = ""
            name = path.name
            mentioned = sorted(t for t, text in texts.items() if name in text and t != rel)
            entry = {"project": folder, "file": rel, "bytes": path.stat().st_size, "sha256": sha,
                     "mentioned_in": mentioned[:12], "maker": {"kind": PRODUCER, "file": renders[sha]}
                     if sha in renders else {"kind": "unknown"}}
            key = f"{folder}:{rel}"
            record = by_sha.get(sha) or by_path.get(key) or (by_path.get(rel) if folder == "neutrinohit-map" else None)
            film = film_of.get(mr.key(record)) if record else None
            if film and sha in renders and film["maker"]["kind"] in ("unknown", "footer"):
                film["maker"] = {"kind": PRODUCER, "scene": renders[sha].split("/")[0], "file": renders[sha]}
            rule = next((pattern for pattern in kept if fnmatch.fnmatchcase(key, pattern)), None)
            if rule:
                entry["state"] = "kept"
                entry["reason"] = kept[rule]
                if record:
                    entry["film"] = mr.key(record)
            elif record:
                entry["state"] = "copy"           # bytes of a registered film: switch to nh-video, remove
                entry["film"] = mr.key(record)
            else:
                entry["state"] = "unregistered"
            files.append(entry)
    for kept_path in kept:
        project, _, rel = kept_path.partition(":")
        if not any(ch in rel for ch in "*?[") and not (WORKSPACE / project / rel).is_file():
            files.append({"project": project, "file": rel, "state": "kept-missing", "reason": kept[kept_path]})
    published_sha = set(by_sha)
    unpublished = [f for f in finals if f["sha256"] not in published_sha]
    hashes.save()
    return {"schema": 1, "films": films, "repo_files": files, "dvnanima_unpublished": unpublished,
            "projects": {home: {"title": p["title"], "budget_bytes": p["budget_bytes"],
                                "bytes": sum(r["bytes"] for r in catalog["media"] if r["home"] == home)}
                         for home, p in catalog["projects"].items()}}


def problems(data: dict[str, Any]) -> list[str]:
    """Rule violations: video files in repositories outside the media library."""
    out = []
    for entry in data["repo_files"]:
        if entry["state"] == "unregistered":
            out.append(f'{entry["project"]}: {entry["file"]} — film outside the media library '
                       f'({entry["bytes"] / 1e6:.1f} MB): register it (nh_media.py prepare) or list it in media.kept.json')
        elif entry["state"] == "copy":
            out.append(f'{entry["project"]}: {entry["file"]} — copy of the published {entry["film"]}: '
                       f'insert it with nh-video and remove the copy')
        elif entry["state"] == "kept-missing":
            out.append(f'{entry["project"]}: {entry["file"]} — listed in media.kept.json but gone: remove the entry')
    return out
