#!/usr/bin/env python3
"""Build the NeutrinoHit animation gallery (ru|en/animations.qmd) from local dvnanima renders.

The English page takes title_en, summary_en, description_en and label_en from the catalog;
an English version of a film is the video right after its Russian version.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from build_book_animations import KATEX  # same KaTeX as the QR pages; descriptions may contain $...$


SITE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SITE_ROOT / "animations.catalog.json"
DEFAULT_DVNANIMA_ROOT = SITE_ROOT.parent / "dvnanima"
DEFAULT_ASSET_DIR = SITE_ROOT / "assets" / "animations" / "dvnanima"
DEFAULT_OUTPUT = SITE_ROOT / "ru" / "animations.qmd"


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
    parser.add_argument("--item", action="append", default=[], metavar="SECTION/ITEM",
                        help="refresh only these items' media; keep all gallery cards")
    parser.add_argument("--transcode-threshold-mb", type=float, default=4.0)
    parser.add_argument("--render-only", action="store_true",
                        help="rewrite the page from the published assets; touch no media")
    parser.add_argument("--posters-only", action="store_true",
                        help="rebuild the posters of the --item stories (all if none) from the published "
                             "movies at their poster_time, then rewrite the pages; movies are not touched")
    return parser.parse_args()


PRIVATE_REPOSITORY = re.compile(r"github\.com/[^/\s\"]+/dvnanima\b")


def load_catalog(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if PRIVATE_REPOSITORY.search(text):
        raise ValueError(f"{path}: links to the private dvnanima repository are not published")
    return json.loads(text)


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


def resolve_video_source(video: dict[str, Any], dvnanima_root: Path) -> Path:
    source_path = video.get("source_path")
    if not source_path:
        return dvnanima_root / video["path"]

    source = Path(source_path)
    if source.is_absolute():
        return source
    return SITE_ROOT.parent / source


def build_poster(
    source: Path,
    target: Path,
    force: bool,
    poster_time: float = 0.35,
) -> None:
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
            str(poster_time),
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
    only_items: set[tuple[str, str]] | None = None,
) -> dict[tuple[str, str, str], dict[str, str]]:
    ffmpeg = shell_available("ffmpeg")
    asset_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[tuple[str, str, str], dict[str, str]] = {}

    for section in catalog["sections"]:
        section_id = section["id"]
        for item in section["items"]:
            item_id = item["id"]
            selected = not only_items or (section_id, item_id) in only_items
            for video in item["videos"]:
                video_id = video["id"]
                source = resolve_video_source(video, dvnanima_root)
                if selected and not source.exists():
                    raise FileNotFoundError(f"Missing animation source: {source}")
                poster_time = float(video.get("poster_time", 0.35))

                if video.get("publish_with_project_site"):
                    source_path = Path(video["source_path"])
                    if source_path.is_absolute():
                        raise ValueError(
                            "publish_with_project_site requires a workspace-relative source_path"
                        )
                    poster_source = source.with_suffix(".jpg")
                    if selected:
                        build_poster(source, poster_source, force, poster_time)
                    assets[(section_id, item_id, video_id)] = {
                        "movie": source_path.as_posix(),
                        "poster": source_path.with_suffix(".jpg").as_posix()
                        if poster_source.exists()
                        else "",
                        "size": human_size(source),
                    }
                    continue

                stem = f"{section_id}-{item_id}-{video_id}"
                movie = asset_dir / f"{stem}.mp4"
                poster = asset_dir / f"{stem}.jpg"

                if selected and not skip_video_sync and needs_update(source, movie, force):
                    source_mb = source.stat().st_size / (1024 * 1024)
                    if (
                        copy_only
                        or video.get("copy_only")
                        or not ffmpeg
                        or source_mb <= transcode_threshold_mb
                    ):
                        copy_video(source, movie)
                    else:
                        transcode_video(source, movie)

                if selected:
                    build_poster(source, poster, force, poster_time)

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


def rebuild_posters(catalog: dict[str, Any], asset_dir: Path, items: set[tuple[str, str]]) -> None:
    """Posters from the published movies (no dvnanima sources needed), at each video's poster_time."""
    for section in catalog["sections"]:
        for item in section["items"]:
            if (section["id"], item["id"]) not in items:
                continue
            for video in item["videos"]:
                if video.get("publish_with_project_site"):
                    continue
                stem = f'{section["id"]}-{item["id"]}-{video["id"]}'
                build_poster(asset_dir / f"{stem}.mp4", asset_dir / f"{stem}.jpg", True,
                             float(video.get("poster_time", 0.35)))


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


TEXT = {
    "ru": {
        "title": "Анимации",
        "lead": "Научные анимации NeutrinoHit по темам. Кадр запускает ролик прямо на странице; "
                "кнопки под описанием — другие ролики сюжета и версии на другом языке.",
        "count": lambda stories, videos: (plural_ru(stories, "сюжет", "сюжета", "сюжетов") + " · "
                                          + plural_ru(videos, "ролик", "ролика", "роликов")),
        "topics": "Темы галереи",
        "play": "Смотреть",
        "code": "Код",
        "size": "MP4",
    },
    "en": {
        "title": "Animations",
        "lead": "Scientific animations of NeutrinoHit by topic. A frame plays its video right on the page; "
                "the buttons below the description open the other videos of the story and the versions "
                "in the other language.",
        "count": lambda stories, videos: f"{stories} stories · {videos} videos",
        "topics": "Gallery topics",
        "play": "Play",
        "code": "Code",
        "size": "MP4",
    },
}

# A film with a Russian and an English version is two videos in the catalog, the English one
# right after the Russian one; their labels carry "(русская версия)" / "(English version)".
VERSION = re.compile(r"\s*\((русская версия|English version)\)|^(Русская версия|English version)\b\s*")

PLAYER_JS = """<script>
document.addEventListener('click', function (event) {
  var text = event.target.closest('.anim-text');
  if (text) { text.closest('.anim-card').classList.add('is-open'); return; }
  var link = event.target.closest('.anim-card [data-play]');
  if (!link) return;
  event.preventDefault();
  var card = link.closest('.anim-card');
  var media = card.querySelector('.anim-media');
  document.querySelectorAll('.anim-media video').forEach(function (v) { v.pause(); });
  var video = document.createElement('video');
  video.controls = true; video.playsInline = true; video.autoplay = true; video.preload = 'auto';
  if (link.dataset.poster) video.poster = link.dataset.poster;
  video.src = link.getAttribute('href');
  media.replaceChildren(video);
  card.classList.add('is-open');
  card.querySelectorAll('.anim-chip').forEach(function (chip) {
    chip.classList.toggle('is-current', chip.getAttribute('href') === link.getAttribute('href'));
  });
});
</script>"""


def video_lang(video: dict[str, Any]) -> str:
    label = video["label"]
    if "English version" in label:
        return "en"
    if "русская версия" in label or label.startswith("Русская версия"):
        return "ru"
    return ""


def films_of(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Group the videos of a story into films; a film keeps its language versions together."""
    films: list[dict[str, Any]] = []
    for video in item["videos"]:
        lang = video_lang(video)
        if lang == "en" and films and "ru" in films[-1]["versions"] and "en" not in films[-1]["versions"]:
            films[-1]["versions"]["en"] = video
            films[-1]["label_en"] = VERSION.sub("", video["label"]).strip()
            continue
        films.append({"label": VERSION.sub("", video["label"]).strip(), "label_en": video.get("label_en"),
                      "versions": {lang or "any": video}})
    return films


def render_qmd(
    catalog: dict[str, Any],
    assets: dict[tuple[str, str, str], dict[str, str]],
    output_path: Path,
    lang: str = "ru",
) -> str:
    text = TEXT[lang]
    other = "en" if lang == "ru" else "ru"

    def tr(entry: dict[str, Any], key: str) -> str:
        return entry.get(f"{key}_{lang}") or entry[key] if lang != "ru" else entry[key]

    def rel(site_path: str) -> str:
        return Path(os.path.relpath(SITE_ROOT / site_path, output_path.resolve().parent)).as_posix()

    def chip(section: dict, item: dict, video: dict, label: str, extra: str = "") -> str:
        asset = assets[(section["id"], item["id"], video["id"])]
        poster = f' data-poster="{esc(rel(asset["poster"]))}"' if asset["poster"] else ""
        return (f'<a class="anim-chip{extra}" href="{esc(rel(asset["movie"]))}" data-play{poster} '
                f'title="{esc(text["size"])}, {esc(asset["size"])}">{esc(label)}</a>')

    def card(section: dict, item: dict) -> list[str]:
        films = films_of(item)
        first = films[0]["versions"]
        default = first.get(lang) or first.get("ru") or first.get("any") or first["en"]
        asset = assets[(section["id"], item["id"], default["id"])]
        poster = rel(asset["poster"]) if asset["poster"] else ""
        image = (f'<img src="{esc(poster)}" alt="" loading="lazy">' if poster
                 else '<span class="anim-noposter"></span>')
        chips = []
        for film in films:
            versions = film["versions"]
            main = versions.get(lang) or versions.get("ru") or versions.get("any") or versions["en"]
            if len(films) == 1:
                if len(versions) > 1:                      # one film: the language versions only
                    chips += [chip(section, item, versions[code], code.upper(),
                                   " is-current" if versions[code] is default else "")
                              for code in (lang, other) if code in versions]
                continue
            label = film.get("label_en") if lang == "en" and film.get("label_en") else film["label"]
            chips.append(chip(section, item, main, label, " is-current" if main is default else ""))
            if other in versions and versions[other] is not main:
                chips.append(chip(section, item, versions[other], other.upper(), " is-lang"))
        if item.get("source_url"):   # dvnanima is private: only an explicit public repository is linked
            chips.append(f'<a class="anim-chip is-code" href="{esc(item["source_url"])}" rel="noopener">'
                         f'{esc(text["code"])}</a>')
        anchor = f'animation-{section["id"]}-{item["id"]}'
        out = [
            f'      <article class="anim-card" id="{esc(anchor)}">',
            f'        <div class="anim-media"><a class="anim-poster" href="{esc(rel(asset["movie"]))}" data-play'
            + (f' data-poster="{esc(poster)}"' if poster else "")
            + f' aria-label="{esc(text["play"])}: {esc(tr(item, "title"))}">{image}'
            '<span class="anim-play" aria-hidden="true"></span></a></div>',
            f'        <h3 class="anim-title">{esc(tr(item, "title"))}</h3>',
            f'        <p class="anim-text">{esc(tr(item, "description"))}</p>',
        ]
        if chips:
            out.append(f'        <div class="anim-chips">{"".join(chips)}</div>')
        out.append("      </article>")
        return out

    sections = catalog["sections"]
    total_items = sum(len(section["items"]) for section in sections)
    total_videos = sum(count_videos(section) for section in sections)
    lines = [
        "---",
        f'title: "{text["title"]}"',
        "lang: ru-RU" if lang == "ru" else "lang: en-US",
        "toc: false",
        "---",
        "",
        "<!-- Generated by scripts/sync_dvnanima_gallery.py. Edit animations.catalog.json. -->",
        "",
        "```{=html}",
        '<div class="lecture-catalog animation-catalog">',
        f'  <p class="lecture-catalog-lead">{esc(text["lead"])}</p>',
        f'  <nav class="anim-topics" aria-label="{esc(text["topics"])}">',
    ]
    for section in sections:
        lines.append(f'    <a href="#{esc(section["id"])}">{esc(tr(section, "title"))}'
                     f'<span>{len(section["items"])}</span></a>')
    lines += ["  </nav>",
              f'  <p class="anim-total">{esc(text["count"](total_items, total_videos))}</p>']
    for section in sections:
        lines += [
            f'  <section class="anim-section" id="{esc(section["id"])}">',
            '    <div class="anim-section-head">',
            f'      <span class="course-tile-status is-ready">'
            f'{esc(text["count"](len(section["items"]), count_videos(section)))}</span>',
            f'      <h2>{esc(tr(section, "title"))}</h2>',
            f'      <p>{esc(tr(section, "summary"))}</p>',
            "    </div>",
            '    <div class="anim-grid">',
        ]
        for item in section["items"]:
            lines += card(section, item)
        lines += ["    </div>", "  </section>"]
    lines.append("</div>")
    lines.append(PLAYER_JS)
    if any("$" in tr(item, "description") for section in sections for item in section["items"]):
        lines.append(KATEX.rstrip("\n"))
    lines.extend(["```", ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    only_items = set()
    known = {(section["id"], item["id"])
             for section in catalog["sections"] for item in section["items"]}
    for token in args.item:
        parts = token.split("/")
        if len(parts) != 2 or tuple(parts) not in known:
            raise ValueError(f"Unknown SECTION/ITEM: {token}")
        only_items.add(tuple(parts))
    if args.posters_only:
        rebuild_posters(catalog, args.asset_dir.resolve(), only_items or known)
    if args.render_only or args.posters_only:
        only_items = {("", "")}                                # nothing selected: no copies, no posters
    assets = sync_assets(
        catalog=catalog,
        dvnanima_root=args.dvnanima_root.resolve(),
        asset_dir=args.asset_dir.resolve(),
        skip_video_sync=args.skip_video_sync,
        copy_only=args.copy_only,
        force=args.force,
        transcode_threshold_mb=args.transcode_threshold_mb,
        only_items=only_items or None,
    )
    # the English page sits next to the Russian one: <root>/ru/animations.qmd -> <root>/en/animations.qmd
    for lang, output in (("ru", args.output), ("en", args.output.parent.parent / "en" / args.output.name)):
        output.write_text(render_qmd(catalog, assets, output, lang), encoding="utf-8")


if __name__ == "__main__":
    main()
