#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GTRACKER_DIR = ROOT.parent / "gTracker"
DEFAULT_SHEET_ID = "1SKOLwN3Z0NBhId9u7V5wXz3iqPsoCJ5_Tp7-h8-mXLo"
DEFAULT_WORKSHEET = "Заявки"
DEFAULT_MP4 = ROOT / "assets/programs/teach-in-applications-map.mp4"
DEFAULT_POSTER = ROOT / "assets/programs/teach-in-applications-map-poster.jpg"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the Teach-in applications map video from the Google Sheet via gTracker."
    )
    parser.add_argument("--sheet-id", default=os.environ.get("GTRACKER_SHEET_ID", DEFAULT_SHEET_ID))
    parser.add_argument("--gid", default=os.environ.get("GTRACKER_GID", "0"))
    parser.add_argument("--worksheet", default=os.environ.get("GTRACKER_WORKSHEET", DEFAULT_WORKSHEET))
    parser.add_argument("--gtracker-dir", type=Path, default=DEFAULT_GTRACKER_DIR)
    parser.add_argument("--python", default=os.environ.get("GTRACKER_PYTHON", sys.executable))
    parser.add_argument("--mp4", type=Path, default=DEFAULT_MP4)
    parser.add_argument("--poster", type=Path, default=DEFAULT_POSTER)
    parser.add_argument("--mp4-fps", type=int, default=1)
    parser.add_argument("--hold-first", type=int, default=2)
    parser.add_argument("--hold-last", type=int, default=10)
    parser.add_argument("--label-top", type=int, default=8)
    parser.add_argument("--network-neighbors", type=int, default=1)
    parser.add_argument("--poster-time", default="7")
    parser.add_argument("--reauth", action="store_true", help="Force a new local OAuth browser flow.")
    parser.add_argument("--stage", action="store_true", help="git add the updated MP4 and poster.")
    parser.add_argument("--dry-run", action="store_true", help="Print the gTracker command without running it.")
    return parser.parse_args()


def token_backed_oauth_client(token_path: Path, target_path: Path) -> Path:
    token = json.loads(token_path.read_text(encoding="utf-8"))
    config = {
        "installed": {
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": token.get("token_uri", "https://oauth2.googleapis.com/token"),
            "redirect_uris": ["http://localhost"],
        }
    }
    target_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def run_command(cmd: list[str], *, cwd: Path, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    print(" ".join(str(part) for part in cmd), flush=True)
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def make_poster(mp4: Path, poster: Path, *, poster_time: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found; install ffmpeg to update the poster")
    poster.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="teachin-map-poster-") as tmp:
        png = Path(tmp) / "poster.png"
        subprocess.run(
            [ffmpeg, "-y", "-ss", poster_time, "-i", str(mp4), "-frames:v", "1", "-update", "1", str(png)],
            check=True,
        )
        Image.open(png).convert("RGB").save(poster, quality=86, optimize=True)


def stage_outputs(paths: list[Path]) -> None:
    subprocess.run(["git", "add", *[str(path.relative_to(ROOT)) for path in paths]], cwd=ROOT, check=True)


def main() -> int:
    args = parse_args()
    gtracker = args.gtracker_dir.resolve()
    build_script = gtracker / "scripts/build_from_google.py"
    token_path = gtracker / "credentials/token.json"
    oauth_client_path = gtracker / "credentials/oauth-client.json"

    if not build_script.exists():
        print(f"gTracker build script not found: {build_script}", file=sys.stderr)
        return 2
    if not token_path.exists():
        print(f"OAuth token not found: {token_path}", file=sys.stderr)
        return 2

    args.mp4.parent.mkdir(parents=True, exist_ok=True)
    args.poster.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="teachin-gtracker-") as tmp:
        tmp_path = Path(tmp)
        frames = tmp_path / "frames"
        raw_csv = tmp_path / "raw_applications.csv"
        normalized_csv = tmp_path / "applications.csv"
        summary = tmp_path / "applications_summary.json"
        oauth_for_run = oauth_client_path
        backup_token_path: Path | None = None

        if args.reauth:
            backup_token_path = token_path.with_name(f"{token_path.name}.bak")
            shutil.copy2(token_path, backup_token_path)
            oauth_for_run = token_backed_oauth_client(token_path, tmp_path / "oauth-client-from-token.json")
            token_path.unlink()
            print(f"Backed up old OAuth token to {backup_token_path}; a browser OAuth flow may open now.")

        cmd = [
            args.python,
            str(build_script),
            "--sheet-id",
            args.sheet_id,
            "--gid",
            args.gid,
            "--worksheet",
            args.worksheet,
            "--oauth-client",
            str(oauth_for_run),
            "--token",
            str(token_path),
            "--raw-csv",
            str(raw_csv),
            "--normalized-csv",
            str(normalized_csv),
            "--summary",
            str(summary),
            "--city-cache",
            str(gtracker / "data/city_cache.csv"),
            "--geojson",
            str(gtracker / "data/ne_110m_admin_0_countries.geojson"),
            "--scope",
            "russia",
            "--download-map",
            "--geocode-missing",
            "--no-gif",
            "--frames",
            str(frames),
            "--mp4",
            str(args.mp4),
            "--date-mode",
            "events",
            "--mp4-fps",
            str(args.mp4_fps),
            "--hold-first",
            str(args.hold_first),
            "--hold-last",
            str(args.hold_last),
            "--label-top",
            str(args.label_top),
            "--network-neighbors",
            str(args.network_neighbors),
        ]

        result = run_command(cmd, cwd=gtracker, dry_run=args.dry_run)
        if result.returncode != 0:
            combined = f"{result.stdout}\n{result.stderr}"
            if "invalid_grant" in combined and not args.reauth:
                print(
                    "\nGoogle OAuth token is no longer valid. Run:\n"
                    "  python scripts/update_teachin_applications_map.py --reauth --stage\n"
                    "and complete the browser authorization once.",
                    file=sys.stderr,
                )
            return result.returncode

    if not args.dry_run:
        make_poster(args.mp4, args.poster, poster_time=args.poster_time)
        if args.stage:
            stage_outputs([args.mp4, args.poster])
        print(f"updated: {args.mp4.relative_to(ROOT)}")
        print(f"updated: {args.poster.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
