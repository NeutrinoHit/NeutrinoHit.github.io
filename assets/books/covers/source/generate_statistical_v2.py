#!/usr/bin/env python3
"""Generate the second working design of the statistical-methods cover."""

from __future__ import annotations

import json
import io
import math
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "neutrinohit-matplotlib")
)
os.environ.setdefault(
    "XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "neutrinohit-xdg-cache")
)

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from generate_series import esc, nested_svg, polyline_path, svg_document, svg_lines


ROOT = Path(__file__).resolve().parents[1]
SERIES_CONFIG = ROOT / "config" / "series.json"
V2_CONFIG = ROOT / "config" / "statistical_v2.json"
DATA = ROOT / "data" / "juno_like_central_figure_v1_data.npz"
LOGO = ROOT / "source" / "brand" / "neutrinohit_logo.svg"
BASE_ART = ROOT / "source" / "artwork" / "statistical_methods_juno.svg"
OUTPUT = ROOT / "svg" / "v2"
ARTWORK_OUTPUT = OUTPUT / "artwork"


def interpolate_crossing(
    point_a: tuple[float, float],
    value_a: float,
    point_b: tuple[float, float],
    value_b: float,
    level: float,
) -> tuple[float, float] | None:
    delta_a = value_a - level
    delta_b = value_b - level
    if delta_a == 0 and delta_b == 0:
        return None
    if delta_a * delta_b > 0:
        return None
    if value_a == value_b:
        fraction = 0.5
    else:
        fraction = (level - value_a) / (value_b - value_a)
    if fraction < 0 or fraction > 1:
        return None
    return (
        point_a[0] + fraction * (point_b[0] - point_a[0]),
        point_a[1] + fraction * (point_b[1] - point_a[1]),
    )


def contour_segments(
    values: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    level: float,
    map_x,
    map_y,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segments = []
    for row in range(len(y_values) - 1):
        for column in range(len(x_values) - 1):
            corners = [
                ((x_values[column], y_values[row]), values[row, column]),
                ((x_values[column + 1], y_values[row]), values[row, column + 1]),
                ((x_values[column + 1], y_values[row + 1]), values[row + 1, column + 1]),
                ((x_values[column], y_values[row + 1]), values[row + 1, column]),
            ]
            crossings = []
            for edge in range(4):
                (point_a, value_a) = corners[edge]
                (point_b, value_b) = corners[(edge + 1) % 4]
                crossing = interpolate_crossing(point_a, value_a, point_b, value_b, level)
                if crossing is not None:
                    mapped = (map_x(crossing[0]), map_y(crossing[1]))
                    if not crossings or math.dist(mapped, crossings[-1]) > 1e-7:
                        crossings.append(mapped)
            if len(crossings) == 2:
                segments.append((crossings[0], crossings[1]))
            elif len(crossings) == 4:
                center = sum(value for _, value in corners) / 4
                if center <= level:
                    segments.extend([(crossings[0], crossings[1]), (crossings[2], crossings[3])])
                else:
                    segments.extend([(crossings[0], crossings[3]), (crossings[1], crossings[2])])
    return segments


def stitch_segments(
    segments: list[tuple[tuple[float, float], tuple[float, float]]]
) -> list[list[tuple[float, float]]]:
    def key(point: tuple[float, float]) -> tuple[float, float]:
        return (round(point[0], 4), round(point[1], 4))

    remaining = list(segments)
    paths = []
    while remaining:
        start, end = remaining.pop()
        path = [start, end]
        extended = True
        while extended and remaining:
            extended = False
            endpoint = key(path[-1])
            for index, (a, b) in enumerate(remaining):
                if key(a) == endpoint:
                    path.append(b)
                elif key(b) == endpoint:
                    path.append(a)
                else:
                    continue
                remaining.pop(index)
                extended = True
                break
        paths.append(path)
    return paths


def contour_paths(
    values: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    level: float,
    map_x,
    map_y,
) -> list[str]:
    paths = []
    for points in stitch_segments(
        contour_segments(values, x_values, y_values, level, map_x, map_y)
    ):
        if len(points) < 3:
            continue
        closed = math.dist(points[0], points[-1]) < 0.25
        paths.append(polyline_path(points) + (" Z" if closed else ""))
    return paths


def detector_group() -> str:
    source = BASE_ART.read_text(encoding="utf-8")
    match = re.search(r'<g id="juno-detector">.*?</g>', source, flags=re.S)
    if not match:
        raise RuntimeError("JUNO detector group was not found in the baseline SVG")
    return match.group(0).replace('id="juno-detector"', 'id="juno-detector-v2"')


def latex_overlay(
    width: float,
    height: float,
    color: str,
    labels: list[tuple[float, float, str, float, str, float]],
) -> str:
    """Render mathtext/LaTeX labels as portable vector paths."""
    with plt.rc_context(
        {
            "mathtext.fontset": "cm",
            "font.family": "serif",
            "svg.fonttype": "path",
        }
    ):
        figure = plt.figure(
            figsize=(width / 72, height / 72),
            dpi=72,
            facecolor="none",
        )
        axes = figure.add_axes([0, 0, 1, 1])
        axes.set_axis_off()
        axes.set_xlim(0, width)
        axes.set_ylim(height, 0)
        for x, y, source, size, align, rotation in labels:
            axes.text(
                x,
                y,
                source,
                fontsize=size,
                ha=align,
                va="center",
                rotation=rotation,
                color=color,
            )

        buffer = io.StringIO()
        figure.savefig(
            buffer,
            format="svg",
            transparent=True,
            metadata={"Date": None},
        )
        plt.close(figure)

    svg = buffer.getvalue()
    inner = re.sub(r"^.*?<svg\b[^>]*>", "", svg, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, count=1, flags=re.S)
    inner = inner.replace("xlink:href", "href")
    ids = re.findall(r'id="([^"]+)"', inner)
    for old in sorted(ids, key=len, reverse=True):
        new = f"statistical_v2_math_{old}"
        inner = inner.replace(f'id="{old}"', f'id="{new}"')
        inner = inner.replace(f'url(#{old})', f'url(#{new})')
        inner = inner.replace(f'href="#{old}"', f'href="#{new}"')
    return inner


def statistical_artwork_v2(colors: dict) -> str:
    data = np.load(DATA)
    dm = data["dm21_grid"] * 1e5
    s12 = data["s12_grid"]
    q = data["q"]
    profile_dm = data["profile_dm21"]
    profile_s12 = data["profile_s12"]
    energy = data["e_centers"]
    spectrum_osc = data["spec_best"]
    spectrum_noosc = data["spec_noosc"]
    residuals = data["residuals"]
    dm_best = float(data["dm21_best"]) * 1e5
    s12_best = float(data["s12_best"])

    ink = colors["ink"]
    teal = colors["series_teal"]
    accent = colors["accent"]
    subtle = colors["subtle"]
    hair = colors["hair"]
    paper = colors["paper"]
    support_family = "Inter, Arial, sans-serif"

    px, py, pw, ph = 80.0, 220.0, 480.0, 310.0
    tx, ty, tw, th = px, 68.0, pw, 96.0
    rpx, rpy, rpw, rph = 595.0, py, 105.0, ph
    sx, sy, sw, sh = 80.0, 650.0, 840.0, 135.0
    rx, ry, rw, rh = 80.0, 846.0, 840.0, 28.0
    dm_min, dm_max = 7.445, 7.542
    s12_min, s12_max = 0.3054, 0.3154

    def mx(value: float) -> float:
        return px + (value - dm_min) / (dm_max - dm_min) * pw

    def my(value: float) -> float:
        return py + ph - (value - s12_min) / (s12_max - s12_min) * ph

    qmax = 7.5
    mask_dm = (dm >= dm_min) & (dm <= dm_max) & (profile_dm <= qmax)
    profile_path = polyline_path(
        [
            (
                tx + (value - dm_min) / (dm_max - dm_min) * tw,
                ty + th - profile / qmax * th,
            )
            for value, profile in zip(dm[mask_dm], profile_dm[mask_dm])
        ]
    )
    mask_s12 = (s12 >= s12_min) & (s12 <= s12_max) & (profile_s12 <= qmax)
    right_profile_path = polyline_path(
        [
            (
                rpx + profile / qmax * rpw,
                rpy + rph - (value - s12_min) / (s12_max - s12_min) * rph,
            )
            for value, profile in zip(s12[mask_s12], profile_s12[mask_s12])
        ]
    )

    contours = []
    contour_style = [
        (11.83, "#DCECEE", "#9FC9CE", 2.5),
        (6.18, "#A8CDD1", "#4E99A5", 2.8),
        (2.30, "#579EAA", teal, 3.2),
    ]
    for level, fill, stroke, width in contour_style:
        for path in contour_paths(q, dm, s12, level, mx, my):
            contours.append(
                f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" opacity="0.94"/>'
            )

    top_profile_grid = []
    for value in [7.45, 7.47, 7.49, 7.51, 7.53]:
        x = tx + (value - dm_min) / (dm_max - dm_min) * tw
        top_profile_grid.append(
            f'<line x1="{x:.2f}" y1="{ty}" x2="{x:.2f}" y2="{ty + th}" stroke="{hair}" stroke-width="1"/>'
        )
    for value in [2, 4, 6]:
        y = ty + th - value / qmax * th
        top_profile_grid.append(
            f'<line x1="{tx}" y1="{y:.2f}" x2="{tx + tw}" y2="{y:.2f}" stroke="{hair}" stroke-width="1"/>'
        )

    grid = []
    for value in [7.45, 7.47, 7.49, 7.51, 7.53]:
        x = mx(value)
        grid.append(f'<line x1="{x:.2f}" y1="{py}" x2="{x:.2f}" y2="{py + ph}" stroke="{hair}" stroke-width="1"/>')
    for value in [0.306, 0.308, 0.310, 0.312, 0.314]:
        y = my(value)
        grid.append(f'<line x1="{px}" y1="{y:.2f}" x2="{px + pw}" y2="{y:.2f}" stroke="{hair}" stroke-width="1"/>')

    right_grid = []
    for value in [2, 4, 6]:
        x = rpx + value / qmax * rpw
        right_grid.append(f'<line x1="{x:.2f}" y1="{rpy}" x2="{x:.2f}" y2="{rpy + rph}" stroke="{hair}" stroke-width="1"/>')
    for value in [0.306, 0.308, 0.310, 0.312, 0.314]:
        y = rpy + rph - (value - s12_min) / (s12_max - s12_min) * rph
        right_grid.append(
            f'<line x1="{rpx}" y1="{y:.2f}" x2="{rpx + rpw}" y2="{y:.2f}" stroke="{hair}" stroke-width="1"/>'
        )

    energy_mask = (energy >= 1.2) & (energy <= 7.0)
    ymax = 5200.0

    def spec_x(value: float) -> float:
        return sx + (value - 1.2) / (7.0 - 1.2) * sw

    def spec_y(value: float) -> float:
        return sy + sh - value / ymax * sh

    noosc_path = polyline_path(
        [(spec_x(e), spec_y(value)) for e, value in zip(energy[energy_mask], spectrum_noosc[energy_mask])]
    )
    osc_path = polyline_path(
        [(spec_x(e), spec_y(value)) for e, value in zip(energy[energy_mask], spectrum_osc[energy_mask])]
    )
    spectrum_grid = []
    for value in [0, 2000, 4000]:
        y = spec_y(value)
        spectrum_grid.append(f'<line x1="{sx}" y1="{y:.2f}" x2="{sx + sw}" y2="{y:.2f}" stroke="{hair}" stroke-width="1"/>')
    for value in [2, 3, 4, 5, 6, 7]:
        x = spec_x(value)
        spectrum_grid.append(f'<line x1="{x:.2f}" y1="{sy + sh}" x2="{x:.2f}" y2="{sy + sh + 7}" stroke="{ink}" stroke-width="1.4"/>')

    residual_nodes = []
    for index in np.where(energy_mask)[0][::2]:
        x = spec_x(float(energy[index]))
        y = ry + rh / 2 - float(residuals[index]) / 3.0 * (rh / 2)
        residual_nodes.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.25" fill="{teal}"/>')

    latex_labels: list[tuple[float, float, str, float, str, float]] = [
        (tx, 47, r"$q_{\mathrm{p}}(\Delta m^2_{21})$", 18, "left", 0),
        (px + pw / 2, py + ph + 55, r"$\Delta m^2_{21}\,[10^{-5}\,\mathrm{eV}^2]$", 22, "center", 0),
        (20, py + ph / 2, r"$\sin^2\theta_{12}$", 22, "center", 90),
        (rpx + rpw / 2, rpy - 23, r"$q_{\mathrm{p}}(\sin^2\theta_{12})$", 17, "center", 0),
        (802, 320, r"$q(\theta)$", 23, "right", 0),
        (812, 320, r"$=-2\ln\lambda(\theta)$", 23, "left", 0),
        (802, 390, r"$\lambda(\theta)$", 23, "right", 0),
        (812, 390, r"$=\frac{L(\theta,\hat{\eta}(\theta))}{L(\hat{\theta},\hat{\eta})}$", 23, "left", 0),
        (sx + sw / 2, sy + sh + 43, r"$E_{\mathrm{vis}}\,[\mathrm{MeV}]$", 20, "center", 0),
        (19, sy + sh / 2, r"$N_{\mathrm{exp}}\,/\,\mathrm{bin}$", 18, "center", 90),
        (38, ry + rh / 2, r"$\frac{n-\hat{\mu}}{\sqrt{\hat{\mu}}}$", 16, "center", 0),
    ]
    for value in [7.45, 7.47, 7.49, 7.51, 7.53]:
        latex_labels.append((mx(value), py + ph + 24, rf"${value:.2f}$", 14, "center", 0))
    for value in [0.306, 0.308, 0.310, 0.312, 0.314]:
        latex_labels.append((px - 12, my(value), rf"${value:.3f}$", 14, "right", 0))
    for value in [0, 2, 4, 6]:
        x = rpx + value / qmax * rpw
        latex_labels.append((x, rpy + rph + 22, rf"${value}$", 13, "center", 0))
    for value in [0, 2000, 4000]:
        latex_labels.append((sx - 12, spec_y(value), rf"${value}$", 14, "right", 0))
    for value in [2, 3, 4, 5, 6, 7]:
        latex_labels.append((spec_x(value), sy + sh + 22, rf"${value}$", 13, "center", 0))
    math_layer = latex_overlay(1000, 930, ink, latex_labels)

    content = f'''
<rect width="1000" height="930" fill="{paper}"/>
{''.join(top_profile_grid)}
<line x1="{tx}" y1="{ty + th}" x2="{tx + tw}" y2="{ty + th}" stroke="{ink}" stroke-width="2"/>
<line x1="{tx}" y1="{ty}" x2="{tx}" y2="{ty + th}" stroke="{ink}" stroke-width="2"/>
<path id="profile-dm21" d="{profile_path}" fill="none" stroke="{teal}" stroke-width="4.2" stroke-linecap="round"/>
{detector_group()}
{''.join(grid)}
{''.join(contours)}
<line x1="{px}" y1="{py + ph}" x2="{px + pw}" y2="{py + ph}" stroke="{ink}" stroke-width="2.3"/>
<line x1="{px}" y1="{py}" x2="{px}" y2="{py + ph}" stroke="{ink}" stroke-width="2.3"/>
<circle cx="{mx(dm_best):.2f}" cy="{my(s12_best):.2f}" r="7" fill="{accent}"/>
<circle cx="{mx(dm_best):.2f}" cy="{my(s12_best):.2f}" r="13" fill="none" stroke="{accent}" stroke-width="2" opacity="0.55"/>
{''.join(right_grid)}
<line x1="{rpx}" y1="{rpy + rph}" x2="{rpx + rpw}" y2="{rpy + rph}" stroke="{ink}" stroke-width="2"/>
<line x1="{rpx}" y1="{rpy}" x2="{rpx}" y2="{rpy + rph}" stroke="{ink}" stroke-width="2"/>
<path id="profile-s12" d="{right_profile_path}" fill="none" stroke="{teal}" stroke-width="4.2" stroke-linecap="round"/>
{''.join(spectrum_grid)}
<line x1="{sx}" y1="{sy + sh}" x2="{sx + sw}" y2="{sy + sh}" stroke="{ink}" stroke-width="2.2"/>
<line x1="{sx}" y1="{sy}" x2="{sx}" y2="{sy + sh}" stroke="{ink}" stroke-width="2.2"/>
<path id="expected-noosc" d="{noosc_path}" fill="none" stroke="{accent}" stroke-width="4.0" stroke-linecap="round"/>
<path id="expected-osc" d="{osc_path}" fill="none" stroke="{teal}" stroke-width="4.5" stroke-linecap="round"/>
<line x1="747" y1="591" x2="790" y2="591" stroke="{accent}" stroke-width="4"/>
<text x="803" y="597" font-family="{support_family}" font-size="16" fill="{ink}">без осцилляций</text>
<line x1="747" y1="620" x2="790" y2="620" stroke="{teal}" stroke-width="4"/>
<text x="803" y="626" font-family="{support_family}" font-size="16" fill="{ink}">с осцилляциями</text>
<line x1="{rx}" y1="{ry + rh / 2}" x2="{rx + rw}" y2="{ry + rh / 2}" stroke="{hair}" stroke-width="1.5"/>
{''.join(residual_nodes)}
{math_layer}
'''
    return svg_document(
        content,
        width=1000,
        height=930,
        title="Статистический анализ JUNO-like модели",
        description="Двумерное профильное правдоподобие, два одномерных профиля, определение отношения правдоподобий, ожидаемые спектры и узкая полоса остатков.",
        metadata="JUNO-like pedagogical model. The two spectrum curves are expectations spec_noosc and spec_best from the stored NPZ; residual points come from the reproducible pseudoexperiment.",
    )


def cover_star_field_v2(colors: dict, variant: str) -> str:
    """Return a deterministic, optional star field for dark cover variants."""

    if not colors.get("star_field", False):
        return ""
    phase = 19 if variant == "front" else 43
    star = colors.get("star", "#F4E9D2")
    cool_star = colors.get("star_cool", "#9BDCE8")
    nodes = []
    for index in range(64):
        x = 5.0 + ((index * 47 + index * index * 11 + phase * 13) % 200)
        y = 7.0 + ((index * 83 + index * index * 7 + phase * 17) % 283)
        if variant == "front" and 27 <= x <= 199 and 34 <= y <= 110:
            continue
        if variant == "back" and 17 <= x <= 181 and 35 <= y <= 292:
            continue
        radius = 0.18 + 0.09 * (index % 4)
        opacity = 0.18 + 0.09 * (index % 5)
        color = cool_star if index % 7 == 0 else star
        nodes.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
            f'fill="{color}" opacity="{opacity:.2f}"/>'
        )
        if index % 23 == 0:
            nodes.append(
                f'<path d="M {x - 1.1:.2f} {y:.2f} H {x + 1.1:.2f} '
                f'M {x:.2f} {y - 1.1:.2f} V {y + 1.1:.2f}" '
                f'fill="none" stroke="{color}" stroke-width="0.18" opacity="0.48"/>'
            )
    return f'<g id="{variant}-cover-star-field">{"".join(nodes)}</g>'


def front_cover_v2(book: dict, series: dict, colors: dict, artwork: str) -> str:
    display = series["fonts"]["display"]
    support = series["fonts"]["support"]
    book_title = " ".join(book["title_lines"])
    title = svg_lines(
        book["title_lines"],
        x=32.0,
        y=56.0,
        size=13.0,
        leading=14.7,
        family=display,
        fill=colors["ink"],
        weight=600,
        letter_spacing=-0.12,
    )
    artwork_node = nested_svg(
        artwork,
        x=23.0,
        y=112.0,
        width=184.0,
        height=171.1,
        prefix=f'{book["slug"]}_v2_front_art',
    )
    content = f'''
<rect width="210" height="297" fill="{colors["paper"]}"/>{cover_star_field_v2(colors, "front")}
<rect x="0" y="0" width="20" height="297" fill="{colors["series_teal"]}"/>
<rect x="20" y="0" width="2.6" height="297" fill="{colors["accent"]}"/>
<line x1="32" y1="37" x2="194" y2="37" stroke="{colors["hair"]}" stroke-width="0.55"/>
{title}
<text x="32" y="87.5" font-family="{esc(support)}" font-size="4.2" font-weight="500" fill="{colors["subtle"]}">{esc(book["subtitle_lines"][0])}</text>
<text x="32" y="104.0" font-family="{esc(display)}" font-size="6.3" font-weight="600" fill="{colors["ink"]}">{esc(series["author"])}</text>
{artwork_node}
<line x1="32" y1="288" x2="194" y2="288" stroke="{colors["hair"]}" stroke-width="0.45"/>
'''
    return svg_document(
        content,
        width=210,
        height=297,
        title=f"{book_title} — передняя обложка, версия 2",
        description="Передняя обложка без логотипов и нумерации, с зарезервированной верхней зоной для издательских знаков.",
        metadata="Working A4 design. Front logo safe zone: x=32..194 mm, y=12..32 mm. No logo, brand wordmark, or series number is rendered on the front.",
    )


def back_cover_v2(book: dict, series: dict, colors: dict, logo: str) -> str:
    display = series["fonts"]["display"]
    support = series["fonts"]["support"]
    brand_ink = colors.get("brand_ink", colors["series_teal"])
    book_title = " ".join(book["title_lines"])
    logo_node = nested_svg(
        logo,
        x=20.0,
        y=13.5,
        width=16.5,
        height=16.5,
        prefix=f'{book["slug"]}_v2_back_logo',
    )
    logo_backplate_color = colors.get("logo_backplate")
    logo_backplate = (
        f'<circle cx="28.25" cy="21.75" r="9.35" fill="{logo_backplate_color}"/>'
        if logo_backplate_color
        else ""
    )
    blurb = svg_lines(
        book["back_blurb_lines"],
        x=20.0,
        y=73.5,
        size=3.75,
        leading=6.1,
        family=support,
        fill=colors["ink"],
    )
    section_nodes = []
    for index, (heading, detail) in enumerate(book["sections"]):
        y = 126.5 + index * 18.4
        section_nodes.append(
            f'<rect x="20" y="{y - 5:.2f}" width="5.5" height="10" rx="2.75" fill="{colors["accent"]}"/>'
            f'<text x="31" y="{y - 0.4:.2f}" font-family="{esc(support)}" font-size="3.65" font-weight="700" fill="{colors["ink"]}">{esc(heading)}</text>'
            f'<text x="31" y="{y + 5.0:.2f}" font-family="{esc(support)}" font-size="3.2" fill="{colors["subtle"]}">{esc(detail)}</text>'
        )
    bio = svg_lines(
        series["author_bio_lines"],
        x=20.0,
        y=239.5,
        size=3.0,
        leading=5.0,
        family=support,
        fill=colors["subtle"],
    )
    content = f'''
<rect width="210" height="297" fill="{colors["paper"]}"/>{cover_star_field_v2(colors, "back")}
<rect x="190" y="0" width="20" height="297" fill="{colors["series_teal"]}"/>
<rect x="187.4" y="0" width="2.6" height="297" fill="{colors["accent"]}"/>
{logo_backplate}
{logo_node}
<text x="41" y="23.8" font-family="{esc(support)}" font-size="3.65" font-weight="700" letter-spacing="0.28" fill="{brand_ink}">NEUTRINOHIT</text>
<line x1="20" y1="37" x2="178" y2="37" stroke="{colors["hair"]}" stroke-width="0.55"/>
<text x="20" y="56" font-family="{esc(display)}" font-size="11.2" font-weight="600" fill="{colors["ink"]}">О книге</text>
{blurb}
<text x="20" y="114.2" font-family="{esc(support)}" font-size="3.15" font-weight="700" letter-spacing="0.42" fill="{brand_ink}">МАРШРУТ ЧИТАТЕЛЯ</text>
{''.join(section_nodes)}
<rect x="20" y="201" width="158" height="16" rx="2.5" fill="{colors["panel"]}"/>
<line x1="26" y1="205" x2="26" y2="213" stroke="{colors["accent"]}" stroke-width="1.5"/>
<text x="31" y="210.7" font-family="{esc(support)}" font-size="3.25" font-weight="600" fill="{colors["ink"]}">{esc(book["audience"])}</text>
<text x="20" y="228" font-family="{esc(support)}" font-size="3.15" font-weight="700" letter-spacing="0.42" fill="{brand_ink}">ОБ АВТОРЕ</text>
{bio}
<line x1="20" y1="278" x2="178" y2="278" stroke="{colors["hair"]}" stroke-width="0.45"/>
<text x="20" y="286" font-family="{esc(support)}" font-size="2.7" font-weight="500" fill="{colors["subtle"]}">neutrinohit.github.io</text>
'''
    return svg_document(
        content,
        width=210,
        height=297,
        title=f"{book_title} — задняя обложка, версия 2",
        description="Задняя обложка с логотипом NeutrinoHit, аннотацией, маршрутом читателя и биографией автора.",
        metadata="Working A4 design. ISBN, barcode, publisher marks, and bleed are intentionally absent.",
    )


def spread_v2(front: str, back: str, book: dict, series: dict, colors: dict) -> str:
    book_title = " ".join(book["title_lines"])
    slug = book["slug"]
    spine_width = float(colors["spine_width_mm_provisional"])
    front_x = 210 + spine_width
    center = 210 + spine_width / 2
    content = f'''
{nested_svg(back, x=0, y=0, width=210, height=297, prefix=f"{slug}_v2_spread_back")}
<rect x="210" y="0" width="{spine_width}" height="297" fill="{colors["series_teal"]}"/>
<rect x="210" y="0" width="{spine_width}" height="10" fill="{colors["accent"]}"/>
<text x="{center}" y="149" text-anchor="middle" transform="rotate(-90 {center} 149)" font-family="{esc(series["fonts"]["support"])}" font-size="4.0" font-weight="700" fill="#FFFFFF">{esc(series["author"])} · {esc(book_title)}</text>
{nested_svg(front, x=front_x, y=0, width=210, height=297, prefix=f"{slug}_v2_spread_front")}
'''
    return svg_document(
        content,
        width=420 + spine_width,
        height=297,
        title=f"{book_title} — разворот обложки, версия 2",
        description="Задняя сторона, временный корешок и лицевая сторона нового рабочего дизайна.",
        metadata=f"Mockup only. Spine width={spine_width:g} mm; no bleed.",
    )


def overview_v2(front: str, back: str, book: dict, series: dict, colors: dict) -> str:
    book_title = " ".join(book["title_lines"])
    slug = book["slug"]
    scale = 0.78
    width = 210 * scale
    height = 297 * scale
    content = f'''
<rect width="365" height="275" fill="#E4E8E5"/>
<text x="18" y="17" font-family="{esc(series["fonts"]["display"])}" font-size="8" font-weight="600" fill="{colors.get("overview_ink", colors["ink"])}">{esc(book_title)} · рабочая версия 2</text>
{nested_svg(front, x=18, y=28, width=width, height=height, prefix=f"{slug}_v2_overview_front")}
{nested_svg(back, x=183, y=28, width=width, height=height, prefix=f"{slug}_v2_overview_back")}
'''
    return svg_document(
        content,
        width=365,
        height=275,
        title=f"{book_title} — обзор рабочей версии 2",
        description="Передняя и задняя обложки рядом.",
    )


def main() -> None:
    series = json.loads(SERIES_CONFIG.read_text(encoding="utf-8"))
    colors = json.loads(V2_CONFIG.read_text(encoding="utf-8"))
    book = next(book for book in series["books"] if book["slug"] == "statistical_methods")
    logo = LOGO.read_text(encoding="utf-8")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ARTWORK_OUTPUT.mkdir(parents=True, exist_ok=True)

    artwork = statistical_artwork_v2(colors)
    front = front_cover_v2(book, series, colors, artwork)
    back = back_cover_v2(book, series, colors, logo)
    spread = spread_v2(front, back, book, series, colors)
    overview = overview_v2(front, back, book, series, colors)

    outputs = {
        ARTWORK_OUTPUT / "statistical_methods.svg": artwork,
        OUTPUT / "statistical_methods_front.svg": front,
        OUTPUT / "statistical_methods_back.svg": back,
        OUTPUT / "statistical_methods_spread_mockup.svg": spread,
        OUTPUT / "statistical_methods_overview.svg": overview,
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
