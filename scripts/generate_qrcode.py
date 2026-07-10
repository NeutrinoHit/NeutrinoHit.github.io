"""Generate a QR code with the NeutrinoHit logo in the center."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from PIL.Image import Resampling


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_LOGO = PROJECT / "assets" / "reveal" / "dvnlogo.png"


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
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color=fill,
        back_color=back,
    ).convert("RGBA")
    return img.resize((side_px, side_px), Resampling.NEAREST)


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


def selfcheck(img: Image.Image, expected: str) -> None:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        print(f"[selfcheck] skipped: OpenCV is unavailable ({exc})")
        return

    bgr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(bgr)
    if data == expected:
        print("[selfcheck] OK")
    elif data:
        print(f"[selfcheck] decoded different data: {data}")
    else:
        print("[selfcheck] failed: QR was not decoded")


def save_image(img: Image.Image, out: Path, *, dpi: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    suffix = out.suffix.lower()
    if suffix == ".png":
        img.save(out, "PNG", dpi=(dpi, dpi))
    elif suffix == ".pdf":
        img.save(out, "PDF", resolution=dpi)
    else:
        raise SystemExit("Output extension must be .png or .pdf")
    print(f"saved: {out.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a QR code with the NeutrinoHit logo.")
    parser.add_argument("--url", required=True, help="URL or text to encode")
    parser.add_argument("--out", type=Path, required=True, help="Output .png or .pdf path")
    parser.add_argument("--logo", type=Path, default=DEFAULT_LOGO, help="Center logo PNG")
    parser.add_argument("--no-logo", action="store_true", help="Do not place a center logo")
    parser.add_argument("--scale", type=float, default=0.28, help="Logo diameter as a fraction of QR side")
    parser.add_argument("--circle", action=argparse.BooleanOptionalAction, default=True, help="Put logo on a white circle")
    parser.add_argument("--ring", type=int, default=8, help="Circle outline width in pixels")
    parser.add_argument("--size", type=int, default=2400, help="QR image side in pixels")
    parser.add_argument("--dpi", type=int, default=600, help="DPI metadata")
    parser.add_argument("--ecc", choices=["L", "M", "Q", "H"], default="H", help="QR error correction level")
    parser.add_argument("--border", type=int, default=6, help="Quiet border in QR modules")
    parser.add_argument("--fill", default="#111111", help="QR foreground color")
    parser.add_argument("--back", default="#FFFFFF", help="QR background color")
    parser.add_argument("--selfcheck", action="store_true", help="Decode result with OpenCV, if available")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    img = make_qr_image(
        args.url,
        side_px=args.size,
        border=args.border,
        ecc=args.ecc,
        fill=args.fill,
        back=args.back,
    )
    if not args.no_logo:
        img = paste_center_logo(
            img,
            args.logo,
            scale=args.scale,
            circle=args.circle,
            ring_px=args.ring,
        )
    if args.selfcheck:
        selfcheck(img, args.url)
    save_image(img, args.out, dpi=args.dpi)


if __name__ == "__main__":
    main()
