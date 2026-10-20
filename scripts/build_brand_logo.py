#!/usr/bin/env python3
"""Vector NeutrinoHit logo from its master raster.

The master is assets/books/qr_center_logo_globe_bw.png (3335 px): a black ring,
a white disc inside it and the drawing (the Earth and the two vertices) in
black, transparent outside the ring. The ring and the disc become exact
circles; the drawing is traced from the raster at twice its resolution.

Writes assets/brand/neutrinohit-logo.svg (white disc, for any background),
neutrinohit-logo-line.svg (no disc, for light paper), their PDF copies and a
1024 px PNG. Needs numpy, Pillow, OpenCV and rsvg-convert.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MAP = Path(__file__).resolve().parents[1]
MASTER = MAP / "assets/books/qr_center_logo_globe_bw.png"
OUT = MAP / "assets/brand"
VIEW = 512.0      # viewBox side of the SVG
UPSCALE = 2       # trace at twice the master resolution for smooth edges
EPS = 0.35        # polygon simplification, in upscaled pixels


def load_gray() -> tuple[np.ndarray, np.ndarray]:
    im = np.asarray(Image.open(MASTER).convert("RGBA")).astype(np.float64) / 255
    alpha, rgb = im[..., 3], im[..., :3].mean(axis=-1)
    darkness = alpha * (1 - rgb)          # 1 = black ink, 0 = white or transparent
    return darkness, alpha


def fit_circle(points: np.ndarray) -> tuple[float, float, float]:
    """Least-squares circle through points (x, y)."""
    x, y = points[:, 0], points[:, 1]
    a = np.column_stack([x, y, np.ones_like(x)])
    b = x * x + y * y
    c = np.linalg.lstsq(a, b, rcond=None)[0]
    cx, cy = c[0] / 2, c[1] / 2
    return cx, cy, float(np.sqrt(c[2] + cx * cx + cy * cy))


def ring_geometry(darkness: np.ndarray, alpha: np.ndarray) -> tuple[float, float, float, float]:
    """Centre, outer and inner radius of the ring, in master pixels."""
    h, w = alpha.shape
    outer = cv2.findContours((alpha > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
    cx, cy, r_out = fit_circle(max(outer, key=cv2.contourArea)[:, 0, :].astype(float))
    # the inner edge of the ring: first light pixel inward along many rays
    inner = []
    for t in np.linspace(0, 2 * np.pi, 720, endpoint=False):
        for r in np.arange(r_out - 2, r_out * 0.6, -0.5):
            x, y = int(round(cx + r * np.cos(t))), int(round(cy + r * np.sin(t)))
            if 0 <= x < w and 0 <= y < h and darkness[y, x] < 0.5:
                inner.append((cx + r * np.cos(t), cy + r * np.sin(t)))
                break
    # rays that hit a drawing line touching the ring give a short radius; drop them
    pts = np.array(inner)
    rad = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    keep = rad > np.median(rad) - 3
    _, _, r_in = fit_circle(pts[keep])
    return cx, cy, r_out, r_in


def drawing_path(darkness: np.ndarray, cx: float, cy: float, r_in: float, scale: float) -> str:
    """Black drawing inside the ring as one even-odd SVG path in viewBox units."""
    h, w = darkness.shape
    big = cv2.resize(darkness, (w * UPSCALE, h * UPSCALE), interpolation=cv2.INTER_CUBIC)
    ink = (big > 0.5).astype(np.uint8)
    yy, xx = np.mgrid[0:h * UPSCALE, 0:w * UPSCALE]
    # keep only what lies inside the inner edge of the ring (a hair inside it)
    inside = np.hypot(xx - cx * UPSCALE, yy - cy * UPSCALE) < (r_in - 1.5) * UPSCALE
    ink &= inside.astype(np.uint8)
    contours, _ = cv2.findContours(ink, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    k = scale / UPSCALE
    for c in contours:
        if cv2.contourArea(c) < 4:
            continue
        poly = cv2.approxPolyDP(c, EPS, True)[:, 0, :].astype(float)
        if len(poly) < 3:
            continue
        pts = " ".join(f"{x * k:.2f},{y * k:.2f}" for x, y in poly)
        parts.append(f"M {pts} Z")
    return " ".join(parts)


def svg(path_d: str, cx: float, cy: float, r_out: float, r_in: float, scale: float, disc: bool) -> str:
    c = (cx * scale, cy * scale)
    stroke = (r_out - r_in) * scale
    r_mid = (r_out + r_in) / 2 * scale
    disc_el = (f'  <circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="{r_mid:.2f}" fill="#fff"/>\n' if disc else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEW:.0f} {VIEW:.0f}" role="img">\n'
            f'  <title>NeutrinoHit</title>\n'
            f'{disc_el}'
            f'  <path fill="#000" fill-rule="evenodd" d="{path_d}"/>\n'
            f'  <circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="{r_mid:.2f}" fill="none" stroke="#000" '
            f'stroke-width="{stroke:.2f}"/>\n'
            f'</svg>\n')


def main() -> None:
    darkness, alpha = load_gray()
    cx, cy, r_out, r_in = ring_geometry(darkness, alpha)
    side = max(darkness.shape)
    scale = VIEW / side
    # centre the ring in the square viewBox
    shift_x, shift_y = side / 2 - cx, side / 2 - cy
    d = drawing_path(darkness, cx, cy, r_in, scale)
    d = _shift(d, shift_x * scale, shift_y * scale)
    cx, cy = side / 2, side / 2
    OUT.mkdir(parents=True, exist_ok=True)
    for name, disc in (("neutrinohit-logo", True), ("neutrinohit-logo-line", False)):
        f = OUT / f"{name}.svg"
        f.write_text(svg(d, cx, cy, r_out, r_in, scale, disc))
        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(f.with_suffix(".pdf")), str(f)], check=True)
    subprocess.run(["rsvg-convert", "-w", "1024", "-h", "1024", "-o", str(OUT / "neutrinohit-logo-1024.png"),
                    str(OUT / "neutrinohit-logo.svg")], check=True)
    print(f"ring: centre ({cx:.1f}, {cy:.1f}) px, radii {r_out:.1f} / {r_in:.1f} px of the master")


def _shift(d: str, dx: float, dy: float) -> str:
    out = []
    for tok in d.split(" "):
        if "," in tok:
            x, y = tok.split(",")
            out.append(f"{float(x) + dx:.2f},{float(y) + dy:.2f}")
        else:
            out.append(tok)
    return " ".join(out)


if __name__ == "__main__":
    main()
