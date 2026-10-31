#!/usr/bin/env python3
"""Local preview of the whole site with the shared films, as GitHub Pages serves it.

  /                  neutrinohit-map/_site
  /<project>/        <project>/_site of a sibling checkout (talks, neutrinophysics, ...)
  /media-<topic>/    media-<topic>/.work/_site (built by `make check` there)

Supports HTTP Range requests, so video seeking behaves as online. Render the pages
with NH_MEDIA_PREVIEW=1 to let prepared (not yet published) films replace the local
copies. Listens on 127.0.0.1 only.

  python3 scripts/media_preview_server.py [--port 8780]
"""

from __future__ import annotations

import argparse
import http.server
import mimetypes
import os
import re
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = SITE_ROOT.parent
mimetypes.add_type("video/mp4", ".mp4")


def locate(url_path: str) -> Path | None:
    parts = [p for p in url_path.split("/") if p]
    if parts:
        first = parts[0]
        if first.startswith("media-") and (WORKSPACE / first / ".work" / "_site").is_dir():
            base, rest = WORKSPACE / first / ".work" / "_site", parts[1:]
        elif (WORKSPACE / first / "_site").is_dir() and (WORKSPACE / first / ".git").exists():
            base, rest = WORKSPACE / first / "_site", parts[1:]
        else:
            base, rest = SITE_ROOT / "_site", parts
    else:
        base, rest = SITE_ROOT / "_site", []
    path = (base / "/".join(rest)).resolve()
    if not path.is_relative_to(base.resolve()):
        return None
    if path.is_dir():
        path = path / "index.html"
    return path if path.is_file() else None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self) -> None:
        self.serve(head=True)

    def do_GET(self) -> None:
        self.serve(head=False)

    def serve(self, head: bool) -> None:
        url_path = self.path.split("?", 1)[0].split("#", 1)[0]
        if not url_path.endswith("/") and not locate(url_path) and locate(url_path + "/"):
            self.send_response(301)
            self.send_header("Location", url_path + "/")
            self.end_headers()
            return
        path = locate(url_path)
        if path is None:
            self.send_error(404)
            return
        size = path.stat().st_size
        first, last, status = 0, size - 1, 200
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if match and size:
            if match.group(1):
                first = int(match.group(1))
                last = min(int(match.group(2)), size - 1) if match.group(2) else size - 1
            else:
                first = max(size - int(match.group(2) or 0), 0)
            if first > last:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = 206
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(last - first + 1))
        if status == 206:
            self.send_header("Content-Range", f"bytes {first}-{last}/{size}")
        self.end_headers()
        if head:
            return
        with path.open("rb") as handle:
            handle.seek(first)
            remaining = last - first + 1
            try:
                while remaining > 0:
                    block = handle.read(min(1 << 20, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def log_message(self, *args) -> None:
        if os.environ.get("NH_PREVIEW_LOG"):
            super().log_message(*args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{args.port}/  (Ctrl-C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
