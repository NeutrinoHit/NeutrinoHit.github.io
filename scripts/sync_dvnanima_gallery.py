#!/usr/bin/env python3
"""Build the NeutrinoHit animation gallery from local dvnanima renders."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


SITE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SITE_ROOT / "animations.catalog.json"
DEFAULT_DVNANIMA_ROOT = SITE_ROOT.parent / "dvnanima"
DEFAULT_ASSET_DIR = SITE_ROOT / "assets" / "animations" / "dvnanima"
DEFAULT_OUTPUT = SITE_ROOT / "animations.qmd"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync local dvnanima movies into the NeutrinoHit animation gallery."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--dvnanima-root", type=Path, default=DEFAULT_DVNANIMA_ROOT)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-video-sync", action="store_true")
    parser.add_argument("--copy-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--transcode-threshold-mb", type=float, default=4.0)
    return parser.parse_args()


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def shell_available(name: str) -> bool:
    return shutil.which(name) is not None


def needs_update(source: Path, target: Path, force: bool) -> bool:
    if force or not target.exists():
        return True
    return source.stat().st_mtime > target.stat().st_mtime


def human_size(path: Path) -> str:
    size = path.stat().st_size
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def transcode_video(source: Path, target: Path) -> None:
    tmp = target.with_suffix(".tmp.mp4")
    if tmp.exists():
        tmp.unlink()
    video_filter = (
        "fps=30,"
        "scale=if(gt(iw/ih\\,16/9)\\,min(1280\\,iw)\\,-2):"
        "if(gt(iw/ih\\,16/9)\\,-2\\,min(720\\,ih))"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            video_filter,
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    tmp.replace(target)


def copy_video(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def build_poster(source: Path, target: Path, force: bool) -> None:
    if not shell_available("ffmpeg") or not needs_update(source, target, force):
        return
    tmp = target.with_suffix(".tmp.jpg")
    if tmp.exists():
        tmp.unlink()
    poster_filter = (
        "scale=if(gt(iw/ih\\,16/9)\\,min(960\\,iw)\\,-2):"
        "if(gt(iw/ih\\,16/9)\\,-2\\,min(540\\,ih))"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "0.35",
            "-i",
            str(source),
            "-vframes",
            "1",
            "-vf",
            poster_filter,
            "-q:v",
            "4",
            str(tmp),
        ]
    )
    tmp.replace(target)


def sync_assets(
    catalog: dict[str, Any],
    dvnanima_root: Path,
    asset_dir: Path,
    skip_video_sync: bool,
    copy_only: bool,
    force: bool,
    transcode_threshold_mb: float,
) -> dict[tuple[str, str, str], dict[str, str]]:
    ffmpeg = shell_available("ffmpeg")
    asset_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[tuple[str, str, str], dict[str, str]] = {}

    for section in catalog["sections"]:
        section_id = section["id"]
        for item in section["items"]:
            item_id = item["id"]
            for video in item["videos"]:
                video_id = video["id"]
                source = dvnanima_root / video["path"]
                if not source.exists():
                    raise FileNotFoundError(f"Missing animation source: {source}")

                stem = f"{section_id}-{item_id}-{video_id}"
                movie = asset_dir / f"{stem}.mp4"
                poster = asset_dir / f"{stem}.jpg"

                if not skip_video_sync and needs_update(source, movie, force):
                    source_mb = source.stat().st_size / (1024 * 1024)
                    if copy_only or not ffmpeg or source_mb <= transcode_threshold_mb:
                        copy_video(source, movie)
                    else:
                        transcode_video(source, movie)

                build_poster(source, poster, force)

                if not movie.exists():
                    raise FileNotFoundError(f"Missing synced animation asset: {movie}")

                assets[(section_id, item_id, video_id)] = {
                    "movie": movie.relative_to(SITE_ROOT).as_posix(),
                    "poster": poster.relative_to(SITE_ROOT).as_posix()
                    if poster.exists()
                    else "",
                    "size": human_size(movie),
                }

    return assets


def count_videos(section: dict[str, Any]) -> int:
    return sum(len(item["videos"]) for item in section["items"])


def plural_ru(number: int, one: str, few: str, many: str) -> str:
    mod10 = number % 10
    mod100 = number % 100
    if mod10 == 1 and mod100 != 11:
        word = one
    elif 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        word = few
    else:
        word = many
    return f"{number} {word}"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_qmd(
    catalog: dict[str, Any],
    assets: dict[tuple[str, str, str], dict[str, str]],
) -> str:
    repository_url = catalog["repository_url"].rstrip("/")
    source_base_url = catalog["source_base_url"].rstrip("/")
    total_items = sum(len(section["items"]) for section in catalog["sections"])
    total_videos = sum(count_videos(section) for section in catalog["sections"])

    lines = [
        "---",
        'title: "Анимации"',
        "---",
        "",
        "<!-- Generated by scripts/sync_dvnanima_gallery.py. Edit animations.catalog.json. -->",
        "",
        "```{=html}",
        '<div class="lecture-catalog animation-catalog">',
        '  <p class="lecture-catalog-lead">',
        "    Подборка научных анимаций из проекта dvnanima. Ролики на этой странице",
        "    опубликованы как облегчённые web-версии, а исходный код хранится в GitHub.",
        "  </p>",
        '  <div class="animation-catalog-meta">',
        f'    <span>{esc(plural_ru(total_items, "сюжет", "сюжета", "сюжетов"))}</span>',
        f'    <span>{esc(plural_ru(total_videos, "ролик", "ролика", "роликов"))}</span>',
        f'    <a href="{esc(repository_url)}">Репозиторий dvnanima</a>',
        "  </div>",
        '  <section class="lecture-course-list animation-section-list" aria-label="Каталог анимаций">',
    ]

    for section_index, section in enumerate(catalog["sections"]):
        section_open = " open" if section_index == 0 else ""
        item_count = len(section["items"])
        video_count = count_videos(section)
        status = (
            f'{plural_ru(item_count, "сюжет", "сюжета", "сюжетов")}, '
            f'{plural_ru(video_count, "ролик", "ролика", "роликов")}'
        )
        lines.extend(
            [
                f'    <details class="lecture-course animation-section animation-section-{esc(section["id"])}"{section_open}>',
                "      <summary>",
                f'        <span class="lecture-course-status">{esc(status)}</span>',
                f'        <span class="lecture-course-title">{esc(section["title"])}</span>',
                "      </summary>",
                '      <div class="lecture-course-body">',
                f'        <p>{esc(section["summary"])}</p>',
                '        <div class="lecture-material-list animation-material-list">',
            ]
        )

        for item_index, item in enumerate(section["items"]):
            item_open = " open" if section_index == 0 and item_index == 0 else ""
            video_status = plural_ru(len(item["videos"]), "ролик", "ролика", "роликов")
            lines.extend(
                [
                    f'          <details class="lecture-material animation-material"{item_open}>',
                    "            <summary>",
                    f'              <span class="animation-material-title">{esc(item["title"])}</span>',
                    f'              <span class="animation-material-count">{esc(video_status)}</span>',
                    "            </summary>",
                    '            <div class="lecture-material-body animation-material-body">',
                    f'              <p>{esc(item["description"])}</p>',
                    '              <div class="animation-video-grid">',
                ]
            )

            for video in item["videos"]:
                asset = assets[(section["id"], item["id"], video["id"])]
                poster_attr = (
                    f' poster="{esc(asset["poster"])}"' if asset["poster"] else ""
                )
                lines.extend(
                    [
                        '                <figure class="animation-video-frame">',
                        f'                  <video controls preload="none" playsinline{poster_attr}>',
                        f'                    <source src="{esc(asset["movie"])}" type="video/mp4">',
                        "                  </video>",
                        "                  <figcaption>",
                        f'                    <span>{esc(video["label"])}</span>',
                        f'                    <small>{esc(asset["size"])}</small>',
                        "                  </figcaption>",
                        "                </figure>",
                    ]
                )

            lines.extend(
                [
                    "              </div>",
                    '              <div class="lecture-course-actions animation-actions">',
                ]
            )
            source_dir = item.get("source_dir")
            if source_dir:
                source_url = f"{source_base_url}/{source_dir.strip('/')}"
                lines.append(
                    f'                <a class="lecture-action-primary" href="{esc(source_url)}">Исходный код</a>'
                )
            for video in item["videos"]:
                asset = assets[(section["id"], item["id"], video["id"])]
                lines.append(
                    f'                <a href="{esc(asset["movie"])}">MP4: {esc(video["label"])}</a>'
                )
            lines.extend(
                [
                    "              </div>",
                    "            </div>",
                    "          </details>",
                ]
            )

        lines.extend(
            [
                "        </div>",
                "      </div>",
                "    </details>",
            ]
        )

    lines.extend(["  </section>", "</div>", "```", ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    assets = sync_assets(
        catalog=catalog,
        dvnanima_root=args.dvnanima_root.resolve(),
        asset_dir=args.asset_dir.resolve(),
        skip_video_sync=args.skip_video_sync,
        copy_only=args.copy_only,
        force=args.force,
        transcode_threshold_mb=args.transcode_threshold_mb,
    )
    args.output.write_text(render_qmd(catalog, assets), encoding="utf-8")


if __name__ == "__main__":
    main()
