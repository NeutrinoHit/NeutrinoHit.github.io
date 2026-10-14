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
    parser.add_argument("--poster-time", default="last", help="Poster frame time in seconds, or 'last'.")
    parser.add_argument("--reauth", action="store_true", help="Force a new local OAuth browser flow.")
    parser.add_argument("--stage", action="store_true", help="git add the updated MP4 and poster.")
    parser.add_argument("--dry-run", action="store_true", help="Print the gTracker command and planned changes; write nothing.")
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


def run_command(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    print(" ".join(str(part) for part in cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def make_poster(mp4: Path, poster: Path, *, poster_time: str) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found; install ffmpeg to update the poster")
    poster.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="teachin-map-poster-") as tmp:
        png = Path(tmp) / "poster.png"
        if poster_time.lower() == "last":
            cmd = [ffmpeg, "-y", "-sseof", "-1", "-i", str(mp4), "-frames:v", "1", "-update", "1", str(png)]
        else:
            cmd = [ffmpeg, "-y", "-ss", poster_time, "-i", str(mp4), "-frames:v", "1", "-update", "1", str(png)]
        subprocess.run(cmd, check=True)
        Image.open(png).convert("RGB").save(poster, quality=86, optimize=True)


def stage_outputs(paths: list[Path]) -> None:
    subprocess.run(["git", "add", *[str(path.relative_to(ROOT)) for path in paths]], cwd=ROOT, check=True)


def build_command(
    args: argparse.Namespace,
    *,
    gtracker: Path,
    build_script: Path,
    token_path: Path,
    oauth_client: Path,
    work_dir: Path,
) -> list[str]:
    return [
        args.python,
        str(build_script),
        "--sheet-id",
        args.sheet_id,
        "--gid",
        args.gid,
        "--worksheet",
        args.worksheet,
        "--oauth-client",
        str(oauth_client),
        "--token",
        str(token_path),
        "--raw-csv",
        str(work_dir / "raw_applications.csv"),
        "--normalized-csv",
        str(work_dir / "applications.csv"),
        "--summary",
        str(work_dir / "applications_summary.json"),
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
        str(work_dir / "frames"),
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


def dry_run(
    args: argparse.Namespace,
    *,
    gtracker: Path,
    build_script: Path,
    token_path: Path,
    oauth_client_path: Path,
    backup_token_path: Path,
) -> int:
    """Report what a real run would do. Reads only; creates, copies or deletes nothing."""
    if not token_path.exists():
        if backup_token_path.exists():
            print(f"would restore missing OAuth token from {backup_token_path}")
        else:
            print(f"OAuth token not found: {token_path}", file=sys.stderr)
            return 2
    work_dir = Path(tempfile.gettempdir()) / "teachin-gtracker-<run>"
    oauth_client = oauth_client_path
    if args.reauth:
        oauth_client = work_dir / "oauth-client-from-token.json"
        print(f"would back up {token_path} to {backup_token_path} and start a browser OAuth flow")
    cmd = build_command(
        args,
        gtracker=gtracker,
        build_script=build_script,
        token_path=token_path,
        oauth_client=oauth_client,
        work_dir=work_dir,
    )
    print(" ".join(str(part) for part in cmd))
    print(f"would update: {args.mp4}")
    print(f"would update: {args.poster}")
    if args.stage:
        print("would stage both files with git add")
    return 0


def main() -> int:
    args = parse_args()
    gtracker = args.gtracker_dir.resolve()
    build_script = gtracker / "scripts/build_from_google.py"
    token_path = gtracker / "credentials/token.json"
    oauth_client_path = gtracker / "credentials/oauth-client.json"
    backup_token_path = token_path.with_name(f"{token_path.name}.bak")

    if not build_script.exists():
        print(f"gTracker build script not found: {build_script}", file=sys.stderr)
        return 2

    if args.dry_run:
        return dry_run(
            args,
            gtracker=gtracker,
            build_script=build_script,
            token_path=token_path,
            oauth_client_path=oauth_client_path,
            backup_token_path=backup_token_path,
        )

    # Everything below may write files: token restore and backup, output folders.
    if not token_path.exists():
        if backup_token_path.exists():
            shutil.copy2(backup_token_path, token_path)
            print(f"Restored missing OAuth token from {backup_token_path}.")
        else:
            print(f"OAuth token not found: {token_path}", file=sys.stderr)
            return 2

    args.mp4.parent.mkdir(parents=True, exist_ok=True)
    args.poster.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="teachin-gtracker-") as tmp:
        tmp_path = Path(tmp)
        oauth_for_run = oauth_client_path

        if args.reauth:
            shutil.copy2(token_path, backup_token_path)
            oauth_for_run = token_backed_oauth_client(token_path, tmp_path / "oauth-client-from-token.json")
            token_path.unlink()
            print(f"Backed up old OAuth token to {backup_token_path}; a browser OAuth flow may open now.")

        cmd = build_command(
            args,
            gtracker=gtracker,
            build_script=build_script,
            token_path=token_path,
            oauth_client=oauth_for_run,
            work_dir=tmp_path,
        )

        result = run_command(cmd, cwd=gtracker)
        if result.returncode != 0:
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            if args.reauth and not token_path.exists() and backup_token_path.exists():
                shutil.copy2(backup_token_path, token_path)
                print(
                    f"OAuth did not complete; restored the previous token from {backup_token_path}.",
                    file=sys.stderr,
                )
            combined = f"{result.stdout}\n{result.stderr}"
            if "invalid_grant" in combined and not args.reauth:
                print(
                    "\nGoogle OAuth token is no longer valid. Run:\n"
                    "  python scripts/update_teachin_applications_map.py --reauth --stage\n"
                    "and complete the browser authorization once.",
                    file=sys.stderr,
                )
            return result.returncode

    make_poster(args.mp4, args.poster, poster_time=args.poster_time)
    if args.stage:
        stage_outputs([args.mp4, args.poster])
    print(f"updated: {args.mp4.relative_to(ROOT)}")
    print(f"updated: {args.poster.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
