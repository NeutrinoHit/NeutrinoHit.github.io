#!/usr/bin/env python3
"""Optimize album media for the static website.

For each album directory, the script:
- rewrites photos as web-sized JPEGs with a maximum edge of 2560 px;
- creates preview JPEGs with a maximum edge of 1280 px;
- updates album.json with preview paths, byte sizes, and MIME types;
- regenerates index.qmd so gallery thumbnails use previews with data-full links.

The script intentionally does not transcode videos. Video quality and file size
tradeoffs should be reviewed separately.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SITE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALBUM_ROOT = SITE_ROOT / "albums"
WEB_MAX_EDGE = 2560
WEB_JPEG_QUALITY = 85
PREVIEW_MAX_EDGE = 1280
PREVIEW_JPEG_QUALITY = 80


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimize NeutrinoHit photo albums for web publishing."
    )
    parser.add_argument(
        "albums",
        nargs="*",
        type=Path,
        help="Album directories. Defaults to every album with album.json.",
    )
    parser.add_argument(
        "--album-root",
        type=Path,
        default=DEFAULT_ALBUM_ROOT,
        help="Root containing album directories.",
    )
    parser.add_argument("--web-max-edge", type=int, default=WEB_MAX_EDGE)
    parser.add_argument("--web-quality", type=int, default=WEB_JPEG_QUALITY)
    parser.add_argument("--preview-max-edge", type=int, default=PREVIEW_MAX_EDGE)
    parser.add_argument("--preview-quality", type=int, default=PREVIEW_JPEG_QUALITY)
    return parser.parse_args()


def run(command: list[str]) -> None:
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def require_image_tool() -> None:
    if shutil.which("magick") is None:
        raise RuntimeError("ImageMagick `magick` is required to optimize album images")


def load_album(album_dir: Path) -> dict[str, Any]:
    path = album_dir / "album.json"
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def save_album(album_dir: Path, album: dict[str, Any]) -> None:
    path = album_dir / "album.json"
    path.write_text(
        json.dumps(album, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def media_items(album: dict[str, Any]) -> list[dict[str, Any]]:
    items = album.get("media") or album.get("photos") or []
    if not isinstance(items, list):
        raise ValueError("album media/photos must be a list")
    return items


def media_kind(item: dict[str, Any]) -> str:
    explicit = str(item.get("type") or item.get("mediaType") or "").lower()
    if explicit == "video":
        return "video"
    mime_type = str(item.get("mimeType") or "").lower()
    if mime_type.startswith("video/"):
        return "video"
    file_name = str(item.get("file") or "").lower()
    if file_name.endswith((".mp4", ".mov", ".m4v", ".avi", ".webm")):
        return "video"
    return "photo"


def preview_path(item: dict[str, Any]) -> str:
    file_path = Path(str(item["file"]))
    return str(Path("previews") / (file_path.stem + ".jpg"))


def optimize_image(source: Path, target: Path, max_edge: int, quality: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp.jpg")
    if tmp.exists():
        tmp.unlink()
    run(
        [
            "magick",
            str(source),
            "-auto-orient",
            "-resize",
            f"{max_edge}x{max_edge}>",
            "-strip",
            "-sampling-factor",
            "4:2:0",
            "-interlace",
            "Plane",
            "-quality",
            str(quality),
            "jpeg:" + str(tmp),
        ]
    )
    tmp.replace(target)


def optimize_referenced_photo(
    album_dir: Path,
    item: dict[str, Any],
    web_max_edge: int,
    web_quality: int,
    preview_max_edge: int,
    preview_quality: int,
) -> None:
    rel = Path(str(item["file"]))
    path = album_dir / rel
    if not path.exists():
        raise FileNotFoundError(path)

    optimize_image(path, path, web_max_edge, web_quality)

    preview_rel = preview_path(item)
    preview = album_dir / preview_rel
    optimize_image(path, preview, preview_max_edge, preview_quality)

    stat = path.stat()
    item["type"] = "photo"
    item["preview"] = preview_rel
    item["bytes"] = stat.st_size
    item["modified"] = datetime.fromtimestamp(
        stat.st_mtime, tz=timezone.utc
    ).isoformat()
    item["mimeType"] = "image/jpeg"


def optimize_unreferenced_photos(
    album_dir: Path,
    referenced: set[str],
    web_max_edge: int,
    web_quality: int,
) -> int:
    photos_dir = album_dir / "photos"
    if not photos_dir.exists():
        return 0

    count = 0
    for path in sorted(photos_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        rel = str(path.relative_to(album_dir))
        if rel in referenced:
            continue
        optimize_image(path, path, web_max_edge, web_quality)
        count += 1
    return count


def update_video_item(album_dir: Path, item: dict[str, Any]) -> None:
    rel = Path(str(item["file"]))
    path = album_dir / rel
    if not path.exists():
        raise FileNotFoundError(path)
    stat = path.stat()
    item["type"] = "video"
    item["bytes"] = stat.st_size
    item["modified"] = datetime.fromtimestamp(
        stat.st_mtime, tz=timezone.utc
    ).isoformat()
    item.setdefault("mimeType", "video/mp4")


def html_paragraphs(text: str) -> str:
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "\n".join(f"<p>{html.escape(part)}</p>" for part in parts)


def render_figure(item: dict[str, Any]) -> str:
    kind = media_kind(item)
    caption = str(item.get("caption") or "").strip()
    caption_html = (
        f"\n<figcaption>{html.escape(caption)}</figcaption>" if caption else "\n"
    )
    if kind == "video":
        poster = str(item.get("preview") or "").strip()
        poster_attr = f' poster="{html.escape(poster)}"' if poster else ""
        mime_type = str(item.get("mimeType") or "video/mp4")
        return (
            '<figure class="published-video">\n'
            f'<video controls preload="metadata" playsinline{poster_attr}>\n'
            f'<source src="{html.escape(str(item["file"]))}" '
            f'type="{html.escape(mime_type)}">\n'
            "</video>"
            f"{caption_html}"
            "</figure>"
        )

    preview = str(item.get("preview") or item["file"])
    return (
        '<figure class="published-photo">\n'
        f'<img src="{html.escape(preview)}" '
        f'data-full="{html.escape(str(item["file"]))}" '
        f'alt="{html.escape(str(item.get("alt") or ""))}" loading="lazy">'
        f"{caption_html}"
        "</figure>"
    )


def render_index(album_dir: Path, album: dict[str, Any]) -> None:
    items = media_items(album)
    title = str(album.get("title") or "Фотоальбом")
    date = str(album.get("date") or "")
    body = str(album.get("postText") or album.get("summary") or "").strip()

    resources = ["photos/**", "previews/**"]
    if (album_dir / "videos").exists():
        resources.append("videos/**")

    lines = ["---", f'title: "{title}"']
    if date:
        lines.append(f'date: "{date}"')
    lines.append("resources:")
    lines.extend(f"  - {resource}" for resource in resources)
    lines.extend(["---", "", "```{=html}"])
    if body:
        lines.append('<div class="album-post-text">')
        lines.append(html_paragraphs(body))
        lines.append("</div>")
        lines.append("")
    lines.append('<div class="published-album">')
    lines.extend(render_figure(item) for item in items)
    lines.append("</div>")
    lines.append("```")
    lines.append("")

    (album_dir / "index.qmd").write_text("\n".join(lines), encoding="utf-8")


def album_dirs(args: argparse.Namespace) -> list[Path]:
    if args.albums:
        return [path.resolve() for path in args.albums]
    return sorted(path for path in args.album_root.iterdir() if (path / "album.json").exists())


def optimize_album(album_dir: Path, args: argparse.Namespace) -> None:
    album = load_album(album_dir)
    items = media_items(album)
    referenced: set[str] = set()
    photo_count = 0
    video_count = 0

    for item in items:
        rel = str(item.get("file") or "")
        if not rel:
            raise ValueError(f"Media item without file in {album_dir}")
        referenced.add(rel)
        if media_kind(item) == "video":
            update_video_item(album_dir, item)
            video_count += 1
        else:
            optimize_referenced_photo(
                album_dir,
                item,
                args.web_max_edge,
                args.web_quality,
                args.preview_max_edge,
                args.preview_quality,
            )
            photo_count += 1

    extra_count = optimize_unreferenced_photos(
        album_dir, referenced, args.web_max_edge, args.web_quality
    )
    album["schema"] = "neutrinohit.photo-album.v2"
    album["generatedAt"] = datetime.now(timezone.utc).isoformat()
    save_album(album_dir, album)
    render_index(album_dir, album)
    print(
        f"{album_dir.relative_to(SITE_ROOT)}: "
        f"{photo_count} photos, {video_count} videos, {extra_count} extra photos"
    )


def main() -> int:
    args = parse_args()
    require_image_tool()
    for album_dir in album_dirs(args):
        optimize_album(album_dir, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
