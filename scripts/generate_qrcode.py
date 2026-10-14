"""Generate NeutrinoHit QR codes: the book standard with the globe logo in the center.

The standard (TheBook, 2026-10-10): rounded modules, error correction H, a quiet
border of 4 modules and the globe logo `assets/books/qr_center_logo_globe_bw.png`
covering 0.32 of the side (0.40 and more is not read reliably by zbar).

One code:
  python scripts/generate_qrcode.py --url https://neutrinohit.github.io/qr/qft/0001/ --out qr.png --selfcheck

Every published item of a book catalog (books.catalog.json -> <book>.catalog.json),
one file per item named after its `qr_file`, encoding `/qr/<slug>/<id>/`:
  python scripts/generate_qrcode.py --book neutrino-physics --out-dir <dir> --fmt png --selfcheck

A long address (QR version 7+, e.g. an applet or a slide) can lose the code under the
logo at some scales; `--robust` checks sides of 200-1100 px (at least 4 px per module,
at most 0.9 of the file side) with zbarimg and falls back to a logo of 0.18, then to
no logo. Other scripts can import `build_qr`, `build_robust_qr` and `save_image`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from PIL.Image import Resampling


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_LOGO = PROJECT / "assets" / "books" / "qr_center_logo_globe_bw.png"
REGISTRY = PROJECT / "books.catalog.json"
DEFAULT_SCALE = 0.32
DEFAULT_BORDER = 4


def require_qrcode():
    try:
        import qrcode
        from qrcode.image.styledpil import StyledPilImage

        try:
            from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
        except Exception:
            from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: qrcode. Install it with:\n"
            "  python -m pip install 'qrcode[pil]'"
        ) from exc
    return qrcode, StyledPilImage, RoundedModuleDrawer


def make_qr_image(
    data: str,
    *,
    side_px: int,
    border: int,
    ecc: str,
    fill: str,
    back: str,
) -> Image.Image:
    qrcode, StyledPilImage, RoundedModuleDrawer = require_qrcode()
    ecc_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    qr = qrcode.QRCode(
        version=None,
        error_correction=ecc_map[ecc],
        border=border,
        box_size=10,
    )
    qr.add_data(data)
    qr.make(fit=True)
    # Whole pixels per module (the side is close to side_px): a non-integer stretch
    # makes uneven modules that zbar misreads at some scales.
    qr.box_size = max(1, round(side_px / (qr.modules_count + 2 * border)))
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color=fill,
        back_color=back,
    ).convert("RGBA")
    return img


def paste_center_logo(
    img: Image.Image,
    logo_path: Path,
    *,
    scale: float,
    circle: bool,
    ring_px: int,
) -> Image.Image:
    out = img.copy()
    side = out.width
    diameter = int(side * scale)
    logo = Image.open(logo_path).convert("RGBA")
    logo = ImageOps.contain(logo, (diameter, diameter), Resampling.LANCZOS)

    if circle:
        badge = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        draw.ellipse([0, 0, diameter - 1, diameter - 1], fill=(255, 255, 255, 255))
        if ring_px > 0:
            draw.ellipse(
                [
                    ring_px // 2,
                    ring_px // 2,
                    diameter - 1 - ring_px // 2,
                    diameter - 1 - ring_px // 2,
                ],
                outline=(0, 0, 0, 255),
                width=ring_px,
            )
        x = (diameter - logo.width) // 2
        y = (diameter - logo.height) // 2
        badge.alpha_composite(logo, (x, y))
        logo = badge

    x = (side - logo.width) // 2
    y = (side - logo.height) // 2
    out.alpha_composite(logo, (x, y))
    return out


def build_qr(
    data: str,
    *,
    logo: Path | None = DEFAULT_LOGO,
    scale: float = DEFAULT_SCALE,
    circle: bool = False,
    ring_px: int = 8,
    side_px: int = 2400,
    border: int = DEFAULT_BORDER,
    ecc: str = "H",
    fill: str = "#111111",
    back: str = "#FFFFFF",
) -> Image.Image:
    """The standard book QR code; `logo=None` gives a plain code."""
    img = make_qr_image(data, side_px=side_px, border=border, ecc=ecc, fill=fill, back=back)
    if logo is not None:
        img = paste_center_logo(img, logo, scale=scale, circle=circle, ring_px=ring_px)
    return img


def decode(img: Image.Image) -> str | None:
    """Decode with zbarimg (the reader the standard is tuned for), else with OpenCV; None if neither is available."""
    if shutil.which("zbarimg"):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "qr.png"
            img.convert("RGB").save(png)
            result = subprocess.run(["zbarimg", "-q", "--raw", str(png)], capture_output=True, text=True)
            return result.stdout.strip()
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(bgr)
    return data


def selfcheck(img: Image.Image, expected: str) -> bool:
    data = decode(img)
    if data is None:
        print("[selfcheck] skipped: neither zbarimg nor OpenCV is available")
        return True
    if data == expected:
        print("[selfcheck] OK")
        return True
    if data:
        print(f"[selfcheck] decoded different data: {data}")
    else:
        print("[selfcheck] failed: QR was not decoded")
    return False


ROBUST_SIDES = tuple(range(200, 1101, 50))  # pixel sides a camera or a 150-600 dpi render may see
MIN_PX_PER_MODULE = 4                       # below this no code is read reliably, logo or not
ROBUST_SCALES = (DEFAULT_SCALE, 0.18, None)  # None: no logo


def unreadable_sides(img: Image.Image, expected: str, sides=ROBUST_SIDES) -> list[int] | None:
    """Sides (px) at which zbarimg does not read the code; None without zbarimg."""
    if not shutil.which("zbarimg"):
        return None
    gray = img.convert("L")
    return [side for side in sides
            if decode(gray.resize((side, side), Resampling.LANCZOS)) != expected]


def build_robust_qr(data: str, **kwargs) -> tuple[Image.Image, float | None]:
    """The standard code if zbar reads it at every size of ROBUST_SIDES (at least 4 px per module),
    else a smaller logo, else no logo.

    A long address (QR version 7 and more) has an alignment pattern in the centre: the logo
    hides it and zbar loses the code at some scales. Short /qr/<slug>/<id>/ addresses do not
    need the fallback.
    """
    logo = kwargs.pop("logo", DEFAULT_LOGO)
    first = kwargs.pop("scale", DEFAULT_SCALE)
    qrcode, _, _ = require_qrcode()
    probe = qrcode.QRCode(error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{kwargs.get('ecc', 'H')}"))
    probe.add_data(data)
    probe.make(fit=True)
    modules = 17 + 4 * probe.version + 2 * kwargs.get("border", DEFAULT_BORDER)
    sides = [side for side in ROBUST_SIDES if side >= MIN_PX_PER_MODULE * modules]
    scales = (first,) + tuple(s for s in ROBUST_SCALES if s != first) if logo is not None else (None,)
    for scale in scales:
        img = build_qr(data, logo=None if scale is None else logo, scale=scale or DEFAULT_SCALE, **kwargs)
        # a resample close to 1:1 rings at the module edges; a renderer does not do that
        bad = unreadable_sides(img, data, [side for side in sides if side <= 0.9 * img.width])
        if bad is None:
            return img, scale
        if not bad:
            if scale != first:
                print(f"[robust] {data}: logo {first} unreadable, used "
                      f"{'no logo' if scale is None else scale}; a short /qr/ address keeps the standard logo")
            return img, scale
    raise SystemExit(f"[robust] {data}: not readable even without a logo")


def save_image(img: Image.Image, out: Path, *, dpi: int = 600) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    suffix = out.suffix.lower()
    if suffix == ".png":
        img.save(out, "PNG", dpi=(dpi, dpi))
    elif suffix == ".pdf":
        img.convert("RGB").save(out, "PDF", resolution=dpi)
    else:
        raise SystemExit("Output extension must be .png or .pdf")
    print(f"saved: {out.resolve()}")


def book_entries(slug: str, include_proposed: bool = False) -> list[tuple[str, str]]:
    """("url", "qr_file") of every published item of a book in books.catalog.json."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    books = {book["slug"]: book for book in registry["books"]}
    if slug not in books:
        raise SystemExit(f"No book {slug!r} in {REGISTRY.name}; known: {', '.join(books)}")
    book = books[slug]
    catalog = json.loads((PROJECT / book["catalog"]).read_text(encoding="utf-8"))
    base = catalog.get("base_url", registry["base_url"])
    entries = []
    for item in sorted(catalog["items"], key=lambda i: i["id"]):
        if include_proposed or item.get("status", "published") == "published":
            entries.append((f'{base}{book["qr_path"]}{item["id"]}/', item["qr_file"]))
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate NeutrinoHit QR codes with the globe logo.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--url", help="URL or text to encode (one code, needs --out)")
    target.add_argument("--book", help="slug in books.catalog.json: one code per published item (needs --out-dir)")
    parser.add_argument("--out", type=Path, help="Output .png or .pdf path (with --url)")
    parser.add_argument("--out-dir", type=Path, help="Output directory (with --book)")
    parser.add_argument("--fmt", choices=["png", "pdf"], help="With --book: output format (default: the qr_file extension)")
    parser.add_argument("--include-proposed", action="store_true", help="With --book: also items with status \"proposed\"")
    parser.add_argument("--logo", type=Path, default=DEFAULT_LOGO, help="Center logo PNG")
    parser.add_argument("--no-logo", action="store_true", help="Do not place a center logo")
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="Logo diameter as a fraction of QR side (0.40+ is unreliable)")
    parser.add_argument("--circle", action=argparse.BooleanOptionalAction, default=False, help="Put logo on a white circle with a ring (the globe logo has its own)")
    parser.add_argument("--ring", type=int, default=8, help="Circle outline width in pixels")
    parser.add_argument("--size", type=int, default=2400, help="QR image side in pixels (rounded to whole pixels per module)")
    parser.add_argument("--dpi", type=int, default=600, help="DPI metadata")
    parser.add_argument("--ecc", choices=["L", "M", "Q", "H"], default="H", help="QR error correction level")
    parser.add_argument("--border", type=int, default=DEFAULT_BORDER, help="Quiet border in QR modules")
    parser.add_argument("--fill", default="#111111", help="QR foreground color")
    parser.add_argument("--back", default="#FFFFFF", help="QR background color")
    parser.add_argument("--selfcheck", action="store_true", help="Decode the result (zbarimg, else OpenCV)")
    parser.add_argument("--robust", action="store_true", help="Check with zbarimg at 200-1100 px (>= 4 px/module, <= 0.9 of the side); fall back to logo 0.18, then no logo")
    args = parser.parse_args()
    if args.url and args.out is None:
        parser.error("--url needs --out")
    if args.book and args.out_dir is None:
        parser.error("--book needs --out-dir")
    return args


def main() -> int:
    args = parse_args()
    if args.url:
        entries = [(args.url, args.out)]
    else:
        entries = []
        for url, qr_file in book_entries(args.book, args.include_proposed):
            out = args.out_dir / qr_file
            entries.append((url, out.with_suffix("." + args.fmt) if args.fmt else out))

    failures = 0
    for url, out in entries:
        make = (lambda *a, **k: build_robust_qr(*a, **k)[0]) if args.robust else build_qr
        img = make(
            url,
            logo=None if args.no_logo else args.logo,
            scale=args.scale,
            circle=args.circle,
            ring_px=args.ring,
            side_px=args.size,
            border=args.border,
            ecc=args.ecc,
            fill=args.fill,
            back=args.back,
        )
        if args.book:
            print(f"{url} -> {out.name}")
        if args.selfcheck and not selfcheck(img, url):
            failures += 1
        save_image(img, out, dpi=args.dpi)
    if args.book:
        print(f"{args.book}: {len(entries)} code(s) -> {args.out_dir}" + (f", {failures} not decoded" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
