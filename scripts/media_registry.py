"""Shared video registry of NeutrinoHit: media.catalog.json.

One published film (story id, variant, version) has one home: a media project
(media-neutrino, media-qft, media-mechanics) whose GitHub Release holds the file
and whose Pages site serves it at

    /<home>/<id>/<variant>-v<version>.mp4      (same origin as the main site)

The site pages, QR pages and lectures refer to that address instead of keeping
their own copy. A record lists in "replaces" the site paths of the copies it
stands for (assets/animations/dvnanima/..., assets/book-animations/...).

Status: "prepared" (hashed and staged in .cache/media/, not online yet) or
"published" (verified on its Pages address). Only published records change a
page; NH_MEDIA_PREVIEW=1 lets prepared records do so too, for a local preview
with the media sites served next to the main one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SITE_ROOT = Path(__file__).resolve().parents[1]
CATALOG = SITE_ROOT / "media.catalog.json"
CACHE = SITE_ROOT / ".cache" / "media"          # content-addressed copies: <sha256>.mp4
STATUSES = ("prepared", "published")


def load(path: Path = CATALOG) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": 1, "url_prefix": "/", "github": "NeutrinoHit", "projects": {}, "media": []}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save(catalog: dict[str, Any], path: Path = CATALOG) -> None:
    catalog["media"].sort(key=lambda r: (r["home"], r["id"], r["variant"], r["version"]))
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def key(record: dict[str, Any]) -> str:
    return f'{record["id"]}/{record["variant"]}/v{record["version"]}'


def file_of(record: dict[str, Any]) -> str:
    """Path of the film inside its media site."""
    return f'{record["id"]}/{record["variant"]}-v{record["version"]}.mp4'


def asset_name(record: dict[str, Any]) -> str:
    """Name of the Release asset (release tag = story id)."""
    return f'{record["id"]}--{record["variant"]}--v{record["version"]}.mp4'


def url_of(record: dict[str, Any], catalog: dict[str, Any]) -> str:
    return f'{catalog.get("url_prefix", "/")}{record["home"]}/{file_of(record)}'


def release_url(record: dict[str, Any], catalog: dict[str, Any]) -> str:
    return (f'https://github.com/{catalog.get("github", "NeutrinoHit")}/{record["home"]}'
            f'/releases/download/{record["id"]}/{asset_name(record)}')


def cached(record: dict[str, Any]) -> Path:
    return CACHE / f'{record["sha256"]}.mp4'


def preview() -> bool:
    return os.environ.get("NH_MEDIA_PREVIEW") == "1"


def live(record: dict[str, Any]) -> bool:
    return record.get("status") == "published" or (preview() and record.get("status") == "prepared")


def human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


class Resolver:
    """Site path of a local copy -> the live shared record that replaces it."""

    def __init__(self, catalog: dict[str, Any] | None = None) -> None:
        self.catalog = catalog if catalog is not None else load()
        self.by_path: dict[str, dict[str, Any]] = {}
        for record in self.catalog["media"]:
            if live(record):
                for path in record.get("replaces", []):
                    self.by_path[path] = record

    def record(self, site_path: str) -> dict[str, Any] | None:
        return self.by_path.get(site_path.lstrip("/"))

    def url(self, site_path: str) -> str | None:
        record = self.record(site_path)
        return url_of(record, self.catalog) if record else None

    def replaced(self) -> set[str]:
        return set(self.by_path)
