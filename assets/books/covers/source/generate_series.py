#!/usr/bin/env python3
"""Generate the NeutrinoHit author-series covers as self-contained SVG files."""

from __future__ import annotations

import cmath
import html
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "series.json"
OUTPUT = ROOT / "svg" / "v1"
ARTWORK_OUTPUT = OUTPUT / "artwork"
LOGO_PATH = ROOT / "source" / "brand" / "neutrinohit_logo.svg"
STATISTICAL_ART_PATH = ROOT / "source" / "artwork" / "statistical_methods_juno.svg"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_lines(
    lines: list[str],
    *,
    x: float,
    y: float,
    size: float,
    leading: float,
    family: str,
    fill: str,
    weight: int | str = 400,
    anchor: str = "start",
    letter_spacing: float | None = None,
    style: str | None = None,
) -> str:
    attrs = [
        f'x="{x:.2f}"',
        f'y="{y:.2f}"',
        f'font-family="{esc(family)}"',
        f'font-size="{size:.2f}"',
        f'font-weight="{weight}"',
        f'fill="{fill}"',
        f'text-anchor="{anchor}"',
    ]
    if letter_spacing is not None:
        attrs.append(f'letter-spacing="{letter_spacing:.2f}"')
    if style:
        attrs.append(f'font-style="{style}"')
    tspans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else leading
        tspans.append(f'<tspan x="{x:.2f}" dy="{dy:.2f}">{esc(line)}</tspan>')
    return f'<text {" ".join(attrs)}>{"".join(tspans)}</text>'


def polyline_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def prefix_ids(svg: str, prefix: str) -> str:
    ids = re.findall(r'id="([^"]+)"', svg)
    for old in sorted(ids, key=len, reverse=True):
        new = f"{prefix}_{old}"
        svg = svg.replace(f'id="{old}"', f'id="{new}"')
        svg = svg.replace(f'url(#{old})', f'url(#{new})')
        svg = svg.replace(f'href="#{old}"', f'href="#{new}"')
        svg = svg.replace(f'xlink:href="#{old}"', f'xlink:href="#{new}"')
        svg = re.sub(
            rf'(aria-labelledby="[^"]*)\b{re.escape(old)}\b',
            lambda match: match.group(1) + new,
            svg,
        )
    return svg


def nested_svg(
    svg: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    prefix: str,
) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"<!DOCTYPE[^>]*>", "", svg)
    svg = prefix_ids(svg.strip(), prefix)
    def replace_root(match: re.Match[str]) -> str:
        attrs = re.sub(r'\s(?:x|y|width|height)="[^"]*"', "", match.group(1))
        return (
            f'<svg x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" '
            f'height="{height:.3f}"{attrs}>'
        )

    return re.sub(r"<svg\b([^>]*)>", replace_root, svg, count=1)


def svg_document(
    content: str,
    *,
    width: float,
    height: float,
    title: str,
    description: str,
    metadata: str = "",
) -> str:
    metadata_node = f"<metadata>{esc(metadata)}</metadata>" if metadata else ""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width:g}mm" height="{height:g}mm"
     viewBox="0 0 {width:g} {height:g}"
     role="img" aria-labelledby="document-title document-description">
  <title id="document-title">{esc(title)}</title>
  <desc id="document-description">{esc(description)}</desc>
  {metadata_node}
  {content}
</svg>
'''


def neutrino_artwork(book: dict, palette: dict, fonts: dict) -> str:
    accent = book["accent"]
    teal = palette["series_teal"]
    ink = palette["ink"]
    subtle = palette["subtle"]
    pale = book["accent_pale"]

    s12 = math.sqrt(0.307)
    s13 = math.sqrt(0.0222)
    s23 = math.sqrt(0.573)
    c12 = math.sqrt(1 - s12 * s12)
    c13 = math.sqrt(1 - s13 * s13)
    c23 = math.sqrt(1 - s23 * s23)
    delta = -math.pi / 2
    eid = cmath.exp(1j * delta)
    emid = cmath.exp(-1j * delta)
    u = [
        [c12 * c13, s12 * c13, s13 * emid],
        [
            -s12 * c23 - c12 * s23 * s13 * eid,
            c12 * c23 - s12 * s23 * s13 * eid,
            s23 * c13,
        ],
        [
            s12 * s23 - c12 * c23 * s13 * eid,
            -c12 * s23 - s12 * c23 * s13 * eid,
            c23 * c13,
        ],
    ]
    dm2 = [0.0, 7.53e-5, 2.453e-3]
    curves: list[list[tuple[float, float]]] = [[], [], []]
    x_max = 1300.0
    for index in range(321):
        lovere = x_max * index / 320
        probs = []
        for beta in range(3):
            amplitude = 0j
            for mass in range(3):
                phase = cmath.exp(-2j * 1.267 * dm2[mass] * lovere)
                amplitude += u[beta][mass] * u[1][mass].conjugate() * phase
            probs.append(abs(amplitude) ** 2)
        norm = sum(probs)
        for beta, probability in enumerate(probs):
            px = 92 + 818 * lovere / x_max
            py = 700 - 430 * probability / max(norm, 1e-12)
            curves[beta].append((px, py))

    packet_colors = [accent, teal, ink]
    packets = []
    for mass in range(3):
        points = []
        for index in range(181):
            px = 110 + 790 * index / 180
            envelope = math.exp(-((px - (470 + 42 * mass)) / 270) ** 2)
            py = 118 + 34 * mass + 12 * envelope * math.sin(0.082 * px + 1.2 * mass)
            points.append((px, py))
        packets.append(
            f'<path d="{polyline_path(points)}" fill="none" stroke="{packet_colors[mass]}" '
            f'stroke-width="{4.2 - mass * 0.55:.2f}" stroke-linecap="round" opacity="{0.92 - mass * 0.18:.2f}"/>'
        )

    grid = []
    for p in [0.0, 0.25, 0.5, 0.75, 1.0]:
        py = 700 - 430 * p
        grid.append(f'<line x1="92" y1="{py:.2f}" x2="910" y2="{py:.2f}" stroke="{palette["hair"]}" stroke-width="1.4"/>')
    for value in [0, 250, 500, 750, 1000, 1250]:
        px = 92 + 818 * value / x_max
        grid.append(f'<line x1="{px:.2f}" y1="700" x2="{px:.2f}" y2="708" stroke="{ink}" stroke-width="1.6"/>')

    legend = []
    labels = [("νₑ", accent), ("νμ", teal), ("ντ", ink)]
    for index, (label, color) in enumerate(labels):
        lx = 640 + 92 * index
        legend.append(f'<line x1="{lx}" y1="235" x2="{lx + 30}" y2="235" stroke="{color}" stroke-width="5"/>')
        legend.append(f'<text x="{lx + 38}" y="242" font-family="{esc(fonts["support"])}" font-size="22" fill="{ink}">{label}</text>')

    content = f'''
<rect width="1000" height="930" fill="#FFFFFF"/>
<rect x="78" y="62" width="844" height="142" rx="24" fill="{pale}" opacity="0.52"/>
<circle cx="96" cy="135" r="18" fill="{accent}"/>
<circle cx="918" cy="135" r="30" fill="none" stroke="{teal}" stroke-width="4"/>
<circle cx="918" cy="135" r="17" fill="none" stroke="{teal}" stroke-width="2" opacity="0.55"/>
<line x1="114" y1="135" x2="888" y2="135" stroke="{palette["hair"]}" stroke-width="2"/>
{''.join(packets)}
<text x="92" y="44" font-family="{esc(fonts["support"])}" font-size="23" font-weight="700" letter-spacing="2.1" fill="{teal}">МАССОВЫЕ СОСТОЯНИЯ</text>
<text x="96" y="178" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="21" font-weight="700" fill="#FFFFFF">νμ</text>
<text x="918" y="181" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="18" font-weight="700" fill="{teal}">P</text>
{''.join(grid)}
<path d="{polyline_path(curves[0])}" fill="none" stroke="{accent}" stroke-width="6.3" stroke-linecap="round"/>
<path d="{polyline_path(curves[1])}" fill="none" stroke="{teal}" stroke-width="6.3" stroke-linecap="round"/>
<path d="{polyline_path(curves[2])}" fill="none" stroke="{ink}" stroke-width="5.0" stroke-linecap="round" opacity="0.67"/>
<line x1="92" y1="700" x2="910" y2="700" stroke="{ink}" stroke-width="2.3"/>
<line x1="92" y1="270" x2="92" y2="700" stroke="{ink}" stroke-width="2.3"/>
<text x="92" y="243" font-family="{esc(fonts["support"])}" font-size="24" font-weight="700" fill="{ink}">P(νμ → να)</text>
{''.join(legend)}
<text x="501" y="770" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="27" fill="{ink}">L / E  [км / ГэВ]</text>
<text x="64" y="488" text-anchor="middle" transform="rotate(-90 64 488)" font-family="{esc(fonts["support"])}" font-size="24" fill="{ink}">вероятность</text>
<text x="92" y="808" font-family="{esc(fonts["support"])}" font-size="19" fill="{subtle}">Трёхфлэйворная вакуумная эволюция для начального νμ.</text>
<text x="92" y="840" font-family="{esc(fonts["support"])}" font-size="17" fill="{subtle}">Параметры и уравнения генерации сохранены вместе с обложкой.</text>
'''
    return svg_document(
        content,
        width=1000,
        height=930,
        title="Трёхфлэйворные осцилляции нейтрино",
        description="Вероятности переходов мюонного нейтрино в электронный, мюонный и тау-флэйворы в вакууме.",
        metadata="Vacuum PMNS evolution; sin²θ12=0.307, sin²θ13=0.0222, sin²θ23=0.573, δCP=-π/2, Δm²21=7.53e-5 eV², Δm²31=2.453e-3 eV².",
    )


def track_path(
    cx: float,
    cy: float,
    theta: float,
    charge: int,
    radius: float,
    reach: float,
    samples: int = 80,
) -> list[tuple[float, float]]:
    center_x = cx + charge * radius * (-math.sin(theta))
    center_y = cy + charge * radius * math.cos(theta)
    phi0 = theta - charge * math.pi / 2
    arc = 2 * radius * math.asin(min(0.999, reach / (2 * radius)))
    points = []
    for index in range(samples + 1):
        distance = arc * index / samples
        phi = phi0 + charge * distance / radius
        points.append((center_x + radius * math.cos(phi), center_y + radius * math.sin(phi)))
    return points


def wedge_path(cx: float, cy: float, r1: float, r2: float, a1: float, a2: float) -> str:
    points = [
        (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1)),
        (cx + r2 * math.cos(a1), cy + r2 * math.sin(a1)),
        (cx + r2 * math.cos(a2), cy + r2 * math.sin(a2)),
        (cx + r1 * math.cos(a2), cy + r1 * math.sin(a2)),
    ]
    return polyline_path(points) + " Z"


def wavy_path(x1: float, y1: float, x2: float, y2: float, waves: int, amplitude: float) -> str:
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    nx = -dy / max(length, 1e-12)
    ny = dx / max(length, 1e-12)
    points = []
    for index in range(waves * 12 + 1):
        t = index / (waves * 12)
        offset = amplitude * math.sin(2 * math.pi * waves * t)
        points.append((x1 + dx * t + nx * offset, y1 + dy * t + ny * offset))
    return polyline_path(points)


def particle_artwork(book: dict, palette: dict, fonts: dict) -> str:
    accent = book["accent"]
    teal = palette["series_teal"]
    ink = palette["ink"]
    subtle = palette["subtle"]
    pale = book["accent_pale"]
    cx, cy = 505.0, 565.0

    rings = []
    for radius, width, opacity in [(88, 2.3, 0.42), (160, 2.2, 0.36), (232, 2.4, 0.42), (292, 3.0, 0.72), (352, 2.0, 0.30)]:
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{teal}" stroke-width="{width}" opacity="{opacity}"/>'
        )
    for spoke in range(24):
        angle = 2 * math.pi * spoke / 24
        rings.append(
            f'<line x1="{cx + 88 * math.cos(angle):.2f}" y1="{cy + 88 * math.sin(angle):.2f}" '
            f'x2="{cx + 292 * math.cos(angle):.2f}" y2="{cy + 292 * math.sin(angle):.2f}" '
            f'stroke="{palette["hair"]}" stroke-width="1.1"/>'
        )

    muon_angles = [math.radians(27), math.radians(207)]
    calorimeter = []
    for index in range(48):
        mid = 2 * math.pi * (index + 0.5) / 48
        proximity = max(
            math.exp(-((math.atan2(math.sin(mid - angle), math.cos(mid - angle))) / 0.19) ** 2)
            for angle in muon_angles
        )
        outer = 310 + 18 * proximity
        color = accent if proximity > 0.42 else teal
        opacity = 0.12 + 0.68 * proximity
        a1 = 2 * math.pi * index / 48 + 0.012
        a2 = 2 * math.pi * (index + 1) / 48 - 0.012
        calorimeter.append(
            f'<path d="{wedge_path(cx, cy, 296, outer, a1, a2)}" fill="{color}" opacity="{opacity:.3f}"/>'
        )

    tracks = []
    track_hits = []
    track_labels = []
    pairs = [
        (27, 1, 920, 425, accent, 5.8, "μ⁺"),
        (207, -1, 920, 425, teal, 5.8, "μ⁻"),
    ]
    for angle_deg, charge, radius, reach, color, width, label in pairs:
        path = track_path(cx, cy, math.radians(angle_deg), charge, radius, reach)
        tracks.append(
            f'<path d="{polyline_path(path)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
        )
        for hit_index in (18, 34, 50, 66):
            hx, hy = path[hit_index]
            track_hits.append(
                f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="5.2" fill="#FFFFFF" stroke="{teal}" stroke-width="2.4"/>'
            )
        end_x, end_y = path[-1]
        anchor = "start" if end_x > cx else "end"
        offset = 14 if end_x > cx else -14
        track_labels.append(
            f'<text x="{end_x + offset:.2f}" y="{end_y + 8:.2f}" text-anchor="{anchor}" '
            f'font-family="{esc(fonts["support"])}" font-size="25" font-weight="700" fill="{color}">{label}</text>'
        )

    content = f'''
<rect width="1000" height="930" fill="#FFFFFF"/>
<rect x="74" y="48" width="852" height="173" rx="24" fill="{pale}" opacity="0.52"/>
<path d="M 108,88 L 306,135" fill="none" stroke="{ink}" stroke-width="5" stroke-linecap="round"/>
<path d="M 108,182 L 306,135" fill="none" stroke="{ink}" stroke-width="5" stroke-linecap="round"/>
<path d="{wavy_path(306, 135, 605, 135, 10, 11)}" fill="none" stroke="{teal}" stroke-width="4.5"/>
<path d="M 605,135 L 886,84" fill="none" stroke="{accent}" stroke-width="5" stroke-linecap="round"/>
<path d="M 605,135 L 886,186" fill="none" stroke="{accent}" stroke-width="5" stroke-linecap="round"/>
<circle cx="306" cy="135" r="9" fill="{teal}"/>
<circle cx="605" cy="135" r="9" fill="{accent}"/>
<text x="92" y="88" font-family="{esc(fonts["support"])}" font-size="25" fill="{ink}">e⁻</text>
<text x="92" y="204" font-family="{esc(fonts["support"])}" font-size="25" fill="{ink}">e⁺</text>
<text x="450" y="112" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="23" font-weight="700" fill="{teal}">γ / Z</text>
<text x="895" y="88" font-family="{esc(fonts["support"])}" font-size="25" fill="{accent}">μ⁻</text>
<text x="895" y="204" font-family="{esc(fonts["support"])}" font-size="25" fill="{accent}">μ⁺</text>
<text x="505" y="260" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="20" font-weight="700" letter-spacing="2" fill="{teal}">АМПЛИТУДА → СОБЫТИЕ</text>
{''.join(rings)}
{''.join(calorimeter)}
{''.join(tracks)}
{''.join(track_hits)}
{''.join(track_labels)}
<circle cx="{cx}" cy="{cy}" r="10" fill="{accent}"/>
<circle cx="{cx}" cy="{cy}" r="22" fill="none" stroke="{accent}" stroke-width="2.5" opacity="0.48"/>
<text x="86" y="888" font-family="{esc(fonts["support"])}" font-size="18" fill="{subtle}">Схематическая поперечная проекция e⁺e⁻ → μ⁺μ⁻; знаки кривизны противоположны.</text>
'''
    return svg_document(
        content,
        width=1000,
        height=930,
        title="От диаграммы процесса к событию в детекторе",
        description="Диаграмма аннигиляции электрона и позитрона и детерминированная схематическая поперечная проекция события.",
        metadata="Conceptual event display, not experimental data. Opposed charged-track pairs conserve transverse momentum pairwise; curvature encodes charge sign in a uniform solenoidal field.",
    )


def rk4_outgoing_radius(radius: float, step: float) -> float:
    def derivative(r: float) -> float:
        return 0.5 * (1.0 - 1.0 / max(r, 0.08))

    k1 = derivative(radius)
    k2 = derivative(radius + step * k1 / 2)
    k3 = derivative(radius + step * k2 / 2)
    k4 = derivative(radius + step * k3)
    return radius + step * (k1 + 2 * k2 + 2 * k3 + k4) / 6


def gravity_artwork(book: dict, palette: dict, fonts: dict) -> str:
    accent = book["accent"]
    teal = palette["series_teal"]
    ink = palette["ink"]
    subtle = palette["subtle"]
    pale = book["accent_pale"]

    x0, x1 = 94.0, 902.0
    y0, y1 = 82.0, 565.0
    r_min, r_max = 0.18, 5.0

    def map_r(radius: float) -> float:
        return x0 + (radius - r_min) / (r_max - r_min) * (x1 - x0)

    rays = []
    initial_radii = [0.38, 0.62, 0.82, 0.97, 1.03, 1.25, 1.70, 2.55, 3.65]
    for index, initial in enumerate(initial_radii):
        radius = initial
        points = []
        steps = 210
        dv = 7.6 / steps
        for step_index in range(steps + 1):
            v = 7.6 * step_index / steps
            if radius >= r_max:
                points.append((map_r(r_max), y0 + (y1 - y0) * v / 7.6))
                break
            points.append((map_r(radius), y0 + (y1 - y0) * v / 7.6))
            if radius <= r_min + 0.015:
                break
            radius = rk4_outgoing_radius(radius, dv)
        color = accent if initial < 1.0 else teal
        width = 4.0 if index in (3, 4) else 2.8
        opacity = 0.88 if index in (3, 4) else 0.48
        rays.append(
            f'<path d="{polyline_path(points)}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-linecap="round"/>'
        )

    ingoing = []
    for fraction in [0.14, 0.31, 0.48, 0.65, 0.82]:
        py = y0 + (y1 - y0) * fraction
        ingoing.append(
            f'<line x1="{x0}" y1="{py:.2f}" x2="{x1}" y2="{py:.2f}" stroke="{palette["hair"]}" stroke-width="1.5"/>'
        )

    chirp = []
    for index in range(521):
        t = index / 520
        tau = max(0.035, 1.04 - t)
        amplitude = min(62.0, 13.0 * tau ** (-0.25))
        phase = -54.0 * tau ** (5.0 / 8.0)
        px = 92 + 620 * t
        py = 760 - amplitude * math.cos(phase)
        chirp.append((px, py))

    horizon_x = map_r(1.0)
    content = f'''
<rect width="1000" height="930" fill="#FFFFFF"/>
<rect x="72" y="58" width="856" height="535" rx="26" fill="{pale}" opacity="0.34"/>
{''.join(ingoing)}
<line x1="{horizon_x:.2f}" y1="{y0}" x2="{horizon_x:.2f}" y2="{y1}" stroke="{accent}" stroke-width="5.2"/>
<line x1="{map_r(r_min):.2f}" y1="{y0}" x2="{map_r(r_min):.2f}" y2="{y1}" stroke="{ink}" stroke-width="7.0"/>
{''.join(rays)}
<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{ink}" stroke-width="2.3"/>
<text x="{horizon_x + 10:.2f}" y="105" font-family="{esc(fonts["support"])}" font-size="21" font-weight="700" fill="{accent}">r = r<tspan baseline-shift="sub" font-size="15">s</tspan></text>
<text x="{map_r(0.48):.2f}" y="554" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="18" fill="{subtle}">внутри</text>
<text x="{map_r(2.8):.2f}" y="554" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="18" fill="{subtle}">снаружи</text>
<text x="94" y="39" font-family="{esc(fonts["support"])}" font-size="22" font-weight="700" letter-spacing="2" fill="{teal}">ИСХОДЯЩИЕ СВЕТОВЫЕ СИГНАЛЫ</text>
<text x="64" y="334" text-anchor="middle" transform="rotate(-90 64 334)" font-family="{esc(fonts["support"])}" font-size="21" fill="{ink}">координата v</text>
<text x="501" y="620" text-anchor="middle" font-family="{esc(fonts["support"])}" font-size="22" fill="{ink}">радиальная координата r / r<tspan baseline-shift="sub" font-size="16">s</tspan></text>
<line x1="92" y1="760" x2="712" y2="760" stroke="{palette["hair"]}" stroke-width="1.5"/>
<path d="{polyline_path(chirp)}" fill="none" stroke="{teal}" stroke-width="4.2" stroke-linecap="round"/>
<path d="M 820,760 L 820,666 M 820,760 L 914,760" fill="none" stroke="{accent}" stroke-width="7" stroke-linecap="round"/>
<circle cx="820" cy="760" r="13" fill="#FFFFFF" stroke="{ink}" stroke-width="3"/>
<circle cx="820" cy="666" r="9" fill="{accent}"/>
<circle cx="914" cy="760" r="9" fill="{accent}"/>
<text x="92" y="865" font-family="{esc(fonts["support"])}" font-size="19" fill="{subtle}">Горизонт в координатах Эддингтона—Финкельштейна и чирп компактной двойной.</text>
'''
    return svg_document(
        content,
        width=1000,
        height=930,
        title="Световые сигналы у горизонта и гравитационно-волновой чирп",
        description="Радиальные исходящие нулевые геодезические в координатах Эддингтона—Финкельштейна и аналитическая форма чирпа.",
        metadata="Outgoing radial null curves integrate dr/dv=(1-rs/r)/2 with rs=1. Inspiral waveform uses leading-order amplitude proportional to tau^-1/4 and phase proportional to tau^5/8.",
    )


def front_cover(book: dict, config: dict, logo_svg: str, artwork_svg: str) -> str:
    palette = config["colors"]
    fonts = config["fonts"]
    teal = palette["series_teal"]
    accent = book["accent"]
    ink = palette["ink"]
    subtle = palette["subtle"]
    hair = palette["hair"]
    title_y = 54.8
    title_leading = 14.6
    subtitle_y = title_y + (len(book["title_lines"]) - 1) * title_leading + 16.8
    author_y = subtitle_y + 17.8
    artwork = nested_svg(
        artwork_svg,
        x=29.5,
        y=110.5,
        width=170.0,
        height=158.1,
        prefix=f'{book["slug"]}_front_art',
    )
    title = svg_lines(
        book["title_lines"],
        x=38.7,
        y=title_y,
        size=book["title_size"],
        leading=title_leading,
        family=fonts["display"],
        fill=ink,
        weight=600,
        letter_spacing=-0.12,
    )
    subtitle = svg_lines(
        book["subtitle_lines"],
        x=39.0,
        y=subtitle_y,
        size=4.15,
        leading=5.5,
        family=fonts["support"],
        fill=subtle,
        weight=500,
    )
    author = svg_lines(
        [config["author"]],
        x=38.8,
        y=author_y,
        size=6.25,
        leading=7.0,
        family=fonts["display"],
        fill=ink,
        weight=600,
        letter_spacing=-0.04,
    )
    content = f'''
<rect width="210" height="297" fill="{palette["paper"]}"/>
<line x1="27.7" y1="0" x2="27.7" y2="297" stroke="{teal}" stroke-width="1.25"/>
<rect x="28.6" y="48.0" width="2.55" height="32.0" fill="{accent}"/>
<line x1="38.5" y1="36.0" x2="191.0" y2="36.0" stroke="{hair}" stroke-width="0.45"/>
{title}
{subtitle}
{author}
{artwork}
<line x1="38.7" y1="277.4" x2="191.0" y2="277.4" stroke="{hair}" stroke-width="0.35"/>
<text x="38.7" y="285.0" font-family="{esc(fonts["support"])}" font-size="2.65" font-weight="500" letter-spacing="0.05" fill="{subtle}">neutrinohit.github.io</text>
'''
    return svg_document(
        content,
        width=210,
        height=297,
        title=f'{" ".join(book["title_lines"])} — передняя обложка',
        description='Передняя обложка книги Дмитрия В. Наумова.',
        metadata="A4 is provisional. Cover display/support text remains live SVG text until trim, spine, and final wording are approved.",
    )


def back_cover(book: dict, config: dict, logo_svg: str) -> str:
    palette = config["colors"]
    fonts = config["fonts"]
    teal = palette["series_teal"]
    accent = book["accent"]
    pale = book["accent_pale"]
    ink = palette["ink"]
    subtle = palette["subtle"]
    hair = palette["hair"]
    logo = nested_svg(logo_svg, x=18.5, y=15.5, width=16.5, height=16.5, prefix=f'{book["slug"]}_back_logo')

    section_nodes = []
    for index, (heading, detail) in enumerate(book["sections"], start=1):
        cy = 127.6 + (index - 1) * 18.3
        section_nodes.append(
            f'<circle cx="24.1" cy="{cy:.2f}" r="4.15" fill="{accent}"/>'
            f'<text x="24.1" y="{cy + 1.25:.2f}" text-anchor="middle" font-family="{esc(fonts["support"])}" '
            f'font-size="3.15" font-weight="700" fill="#FFFFFF">{index}</text>'
            f'<text x="32.0" y="{cy - 0.45:.2f}" font-family="{esc(fonts["support"])}" font-size="3.65" '
            f'font-weight="700" fill="{ink}">{esc(heading)}</text>'
            f'<text x="32.0" y="{cy + 5.0:.2f}" font-family="{esc(fonts["support"])}" font-size="3.25" '
            f'fill="{subtle}">{esc(detail)}</text>'
        )

    blurb = svg_lines(
        book["back_blurb_lines"],
        x=19.0,
        y=73.8,
        size=3.75,
        leading=6.1,
        family=fonts["support"],
        fill=ink,
        weight=400,
    )
    bio = svg_lines(
        config["author_bio_lines"],
        x=19.0,
        y=239.8,
        size=3.05,
        leading=5.0,
        family=fonts["support"],
        fill=subtle,
        weight=400,
    )
    content = f'''
<rect width="210" height="297" fill="{palette["paper"]}"/>
<line x1="182.3" y1="0" x2="182.3" y2="297" stroke="{teal}" stroke-width="1.25"/>
<rect x="178.85" y="48.0" width="2.55" height="32.0" fill="{accent}"/>
{logo}
<text x="39.3" y="24.9" font-family="{esc(fonts["support"])}" font-size="3.55" font-weight="700" letter-spacing="0.27" fill="{teal}">NEUTRINOHIT</text>
<line x1="19.0" y1="36.0" x2="171.5" y2="36.0" stroke="{hair}" stroke-width="0.45"/>
<text x="19.0" y="55.6" font-family="{esc(fonts["display"])}" font-size="11.2" font-weight="600" letter-spacing="-0.1" fill="{ink}">О книге</text>
{blurb}
<text x="19.0" y="115.0" font-family="{esc(fonts["support"])}" font-size="3.15" font-weight="700" letter-spacing="0.42" fill="{teal}">МАРШРУТ ЧИТАТЕЛЯ</text>
{''.join(section_nodes)}
<rect x="19.0" y="201.0" width="152.5" height="16.0" rx="2.2" fill="{pale}"/>
<line x1="25.0" y1="205.0" x2="25.0" y2="213.0" stroke="{accent}" stroke-width="1.5"/>
<text x="30.2" y="210.7" font-family="{esc(fonts["support"])}" font-size="3.3" font-weight="600" fill="{ink}">{esc(book["audience"])}</text>
<text x="19.0" y="228.2" font-family="{esc(fonts["support"])}" font-size="3.15" font-weight="700" letter-spacing="0.42" fill="{teal}">ОБ АВТОРЕ</text>
{bio}
<line x1="19.0" y1="277.4" x2="171.5" y2="277.4" stroke="{hair}" stroke-width="0.35"/>
<text x="19.0" y="285.0" font-family="{esc(fonts["support"])}" font-size="2.65" font-weight="500" letter-spacing="0.05" fill="{subtle}">neutrinohit.github.io</text>
<text x="171.5" y="285.0" text-anchor="end" font-family="{esc(fonts["support"])}" font-size="2.65" font-weight="600" fill="{accent}">{esc(" ".join(book["title_lines"]))}</text>
'''
    return svg_document(
        content,
        width=210,
        height=297,
        title=f'{" ".join(book["title_lines"])} — задняя обложка',
        description='Задняя обложка книги Дмитрия В. Наумова.',
        metadata=f'Editorial source: {book["source_material"]}. ISBN, barcode, publisher marks, and production marks intentionally omitted until production requirements are known.',
    )


def spine_svg(book: dict, config: dict, x: float, width: float) -> str:
    palette = config["colors"]
    fonts = config["fonts"]
    title = " · ".join(book["title_lines"])
    center = x + width / 2
    return f'''
<rect x="{x:.3f}" y="0" width="{width:.3f}" height="297" fill="{palette["series_teal"]}"/>
<rect x="{x:.3f}" y="0" width="{width:.3f}" height="9" fill="{book["accent"]}"/>
<text x="{center:.3f}" y="149" text-anchor="middle" transform="rotate(-90 {center:.3f} 149)" font-family="{esc(fonts["support"])}" font-size="4.0" font-weight="700" letter-spacing="0.15" fill="#FFFFFF">{esc(config["author"])}  ·  {esc(title)}</text>
'''


def spread_mockup(book: dict, config: dict, front: str, back: str) -> str:
    spine_width = float(config["spine_width_mm_provisional"])
    front_x = 210 + spine_width
    content = (
        nested_svg(back, x=0, y=0, width=210, height=297, prefix=f'{book["slug"]}_spread_back')
        + spine_svg(book, config, 210, spine_width)
        + nested_svg(front, x=front_x, y=0, width=210, height=297, prefix=f'{book["slug"]}_spread_front')
    )
    return svg_document(
        content,
        width=420 + spine_width,
        height=297,
        title=f'{" ".join(book["title_lines"])} — разворот обложки',
        description="Макет задней обложки, параметрического корешка и передней обложки.",
        metadata=f'Provisional mockup only. Spine width={spine_width:g} mm must be replaced after final pagination, stock, and printer specification are known. No bleed is included.',
    )


def overview_svg(config: dict, covers: list[tuple[dict, str, str]]) -> str:
    scale = 0.35
    page_width = 210 * scale
    page_height = 297 * scale
    positions = [(19, 28), (205, 28), (19, 148), (205, 148)]
    nodes = [
        '<rect width="390" height="270" fill="#F4F8F8"/>',
        f'<text x="19" y="17" font-family="{esc(config["fonts"]["display"])}" font-size="8" font-weight="600" fill="{config["colors"]["ink"]}">NeutrinoHit · серия учебников</text>',
    ]
    for (book, front, back), (x, y) in zip(covers, positions):
        nodes.append(
            f'<text x="{x}" y="{y - 4}" font-family="{esc(config["fonts"]["support"])}" font-size="3.1" font-weight="700" letter-spacing="0.2" fill="{book["accent"]}">{esc(" ".join(book["title_lines"]))}</text>'
        )
        nodes.append(f'<rect x="{x - 0.8}" y="{y - 0.8}" width="{page_width + 1.6}" height="{page_height + 1.6}" fill="#FFFFFF" stroke="#CCD8DB" stroke-width="0.5"/>')
        nodes.append(nested_svg(front, x=x, y=y, width=page_width, height=page_height, prefix=f'{book["slug"]}_overview_front'))
        back_x = x + page_width + 5
        nodes.append(f'<rect x="{back_x - 0.8}" y="{y - 0.8}" width="{page_width + 1.6}" height="{page_height + 1.6}" fill="#FFFFFF" stroke="#CCD8DB" stroke-width="0.5"/>')
        nodes.append(nested_svg(back, x=back_x, y=y, width=page_width, height=page_height, prefix=f'{book["slug"]}_overview_back'))
    return svg_document(
        "".join(nodes),
        width=390,
        height=270,
        title="Серия учебников NeutrinoHit",
        description="Четыре пары передних и задних обложек в единой визуальной системе.",
        metadata="Overview only; individual cover files remain the production sources.",
    )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ARTWORK_OUTPUT.mkdir(parents=True, exist_ok=True)
    logo_svg = LOGO_PATH.read_text(encoding="utf-8")
    statistical_svg = STATISTICAL_ART_PATH.read_text(encoding="utf-8")
    artwork_generators = {
        "statistical": lambda book: statistical_svg,
        "neutrino": lambda book: neutrino_artwork(book, config["colors"], config["fonts"]),
        "particle": lambda book: particle_artwork(book, config["colors"], config["fonts"]),
        "gravity": lambda book: gravity_artwork(book, config["colors"], config["fonts"]),
    }

    overview_covers = []
    for book in config["books"]:
        artwork = artwork_generators[book["artwork"]](book)
        artwork_path = ARTWORK_OUTPUT / f'{book["slug"]}.svg'
        artwork_path.write_text(artwork, encoding="utf-8")
        front = front_cover(book, config, logo_svg, artwork)
        back = back_cover(book, config, logo_svg)
        spread = spread_mockup(book, config, front, back)
        (OUTPUT / f'{book["slug"]}_front.svg').write_text(front, encoding="utf-8")
        (OUTPUT / f'{book["slug"]}_back.svg').write_text(back, encoding="utf-8")
        (OUTPUT / f'{book["slug"]}_spread_mockup.svg').write_text(spread, encoding="utf-8")
        overview_covers.append((book, front, back))

    (OUTPUT / "series_overview.svg").write_text(
        overview_svg(config, overview_covers), encoding="utf-8"
    )

    generated = sorted(path.relative_to(ROOT) for path in OUTPUT.rglob("*.svg"))
    for path in generated:
        print(path)


if __name__ == "__main__":
    main()
