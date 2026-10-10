"""Lensed accretion-flow silhouette and an exterior, collimating jet.

All curves are editorial geometry, not a Kerr ray-tracing calculation.
The local engine axis points up; the caller positions the complete system.
"""

from __future__ import annotations

import math

from generate_series import polyline_path


def disk_filaments(front: bool) -> str:
    nodes = []
    start = 0 if front else math.pi
    for i in range(64):
        radius = 103 + 3.65 * i
        height = 12 + 0.152 * (radius - 103)
        points = []
        for j in range(129):
            angle = start + math.pi * j / 128
            ripple = 0.6 * math.sin(9 * angle + i * 0.7)
            points.append((radius * math.cos(angle),
                           height * math.sin(angle) + ripple))
        opacity = (0.30 + 0.30 * (1 - i / 64)) * (1 if front else 0.40)
        nodes.append(
            f'<path d="{polyline_path(points)}" fill="none" '
            f'stroke="url(#bh-disk-light)" stroke-width="{1.0 + 0.38 * (i % 3):.2f}" '
            f'opacity="{opacity:.3f}"/>'
        )
    return ''.join(nodes)


def lensed_disk() -> str:
    """Broad primary image above the shadow, compressed secondary below."""

    nodes = []
    for i in range(22):
        a = 118 + 1.04 * i
        h = 112 + 1.14 * i
        wing = 277 + 2.35 * i
        path = (
            f'M {-wing:.2f} 0 C -204 -2 {-a - 13:.2f} -3 {-a:.2f} -40 '
            f'C {-a + 14:.2f} {-h + 30:.2f} -73 {-h:.2f} -8 {-h:.2f} '
            f'C 59 {-h:.2f} {a - 17:.2f} {-h + 35:.2f} {a:.2f} -39 '
            f'C {a + 17:.2f} -4 206 -1 {wing:.2f} 0'
        )
        opacity = 0.32 + 0.55 * math.exp(-((i - 7) / 6) ** 2)
        nodes.append(
            f'<path d="{path}" fill="none" stroke="url(#bh-lensed-light)" '
            f'stroke-width="1.4" opacity="{opacity:.3f}"/>'
        )
    for i in range(13):
        a, h = 110 + 1.4 * i, 83 + 1.35 * i
        path = (f'M -265 2 C -169 7 {-a - 9:.2f} 15 {-a:.2f} 39 '
                f'C -84 {h:.2f} 66 {h + 8:.2f} {a:.2f} 39 '
                f'C {a + 14:.2f} 13 181 6 265 2')
        nodes.append(
            f'<path d="{path}" fill="none" stroke="url(#bh-disk-light)" '
            f'stroke-width="1.15" opacity="{0.44 - i * 0.019:.3f}"/>'
        )
    return ''.join(nodes)


def jet_field_lines(colors: dict) -> str:
    nodes = []
    # The visible magnetic funnel is rooted in the inner accretion flow,
    # outside the apparent shadow. No luminous line leaves the black disk.
    for sign in (-1, 1):
        for i in range(3):
            root = sign * (112 + 14 * i)
            neck = sign * (16 + 5 * i)
            tip = sign * (39 + 12 * i)
            nodes.append(
                f'<path d="M {root} -10 C {root} -73 {neck} -117 {neck} -188 '
                f'C {neck} -287 {tip} -382 {tip} -482" fill="none" '
                f'stroke="url(#bh-field-fade)" stroke-width="{1.45 - i * .2:.2f}"/>'
            )
    for phase in (0, math.pi):
        points = []
        for i in range(144):
            t = i / 143
            y = -164 - 315 * t
            radius = 18 + 31 * t ** 1.3
            points.append((radius * math.sin(phase + 3.5 * math.pi * t), y))
        nodes.append(
            f'<path d="{polyline_path(points)}" fill="none" '
            f'stroke="url(#bh-field-fade)" stroke-width="1.05" opacity="0.58"/>'
        )
    return ''.join(nodes)


def black_hole_sketch(colors: dict, x: float, y: float, angle: float, scale: float) -> str:
    hot, white = colors['disk_hot'], colors['ring_white']
    warm, outer = colors['disk_middle'], colors['disk_outer']
    cyan, blue = colors['jet_light'], colors['jet']
    dark = colors['black_hole']
    return f'''
<g id="black-hole-engine" transform="translate({x:.5f} {y:.5f}) rotate({angle:.8f}) scale({scale})">
<defs>
  <linearGradient id="bh-disk-light" gradientUnits="userSpaceOnUse" x1="-335" y1="0" x2="335" y2="0">
    <stop offset="0" stop-color="{outer}" stop-opacity="0"/>
    <stop offset="0.18" stop-color="{warm}" stop-opacity="0.75"/>
    <stop offset="0.33" stop-color="{white}"/>
    <stop offset="0.49" stop-color="{hot}"/>
    <stop offset="0.72" stop-color="{warm}" stop-opacity="0.7"/>
    <stop offset="1" stop-color="{outer}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="bh-lensed-light" gradientUnits="userSpaceOnUse" x1="-170" y1="0" x2="170" y2="0">
    <stop offset="0" stop-color="{hot}" stop-opacity="0.2"/>
    <stop offset="0.27" stop-color="{white}"/>
    <stop offset="0.49" stop-color="{white}"/>
    <stop offset="0.72" stop-color="{hot}" stop-opacity="0.85"/>
    <stop offset="1" stop-color="{outer}" stop-opacity="0.14"/>
  </linearGradient>
  <radialGradient id="bh-aureole">
    <stop offset="0.48" stop-color="{warm}" stop-opacity="0"/>
    <stop offset="0.72" stop-color="{hot}" stop-opacity="0.13"/>
    <stop offset="1" stop-color="{outer}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="bh-disk-halo">
    <stop offset="0" stop-color="{white}" stop-opacity="0.22"/>
    <stop offset="0.4" stop-color="{warm}" stop-opacity="0.15"/>
    <stop offset="1" stop-color="{outer}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="bh-jet-light" gradientUnits="userSpaceOnUse" x1="0" y1="-115" x2="0" y2="-490">
    <stop offset="0" stop-color="{hot}" stop-opacity="0"/>
    <stop offset="0.12" stop-color="{white}" stop-opacity="0.68"/>
    <stop offset="0.32" stop-color="{cyan}" stop-opacity="0.62"/>
    <stop offset="0.72" stop-color="{blue}" stop-opacity="0.18"/>
    <stop offset="1" stop-color="{cyan}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="bh-field-fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="-490">
    <stop offset="0" stop-color="{hot}" stop-opacity="0.48"/>
    <stop offset="0.34" stop-color="{white}" stop-opacity="0.44"/>
    <stop offset="0.65" stop-color="{cyan}" stop-opacity="0.25"/>
    <stop offset="1" stop-color="{cyan}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="bh-counterjet-light" gradientUnits="userSpaceOnUse" x1="0" y1="105" x2="0" y2="295">
    <stop offset="0" stop-color="{cyan}" stop-opacity="0"/>
    <stop offset="0.25" stop-color="{cyan}" stop-opacity="0.18"/>
    <stop offset="1" stop-color="{blue}" stop-opacity="0"/>
  </linearGradient>
  <mask id="bh-exterior-only" maskUnits="userSpaceOnUse" x="-400" y="-550" width="800" height="900">
    <rect x="-400" y="-550" width="800" height="900" fill="#fff"/>
    <circle r="96" fill="#000"/>
  </mask>
</defs>
<g id="jet-exterior-flow" mask="url(#bh-exterior-only)">
  <path id="counterjet" d="M -77 22 C -35 82 -10 106 -14 165 L -39 295 Q 0 274 39 295 L 14 165 C 10 106 35 82 77 22 Z" fill="url(#bh-counterjet-light)"/>
  <path id="relativistic-jet" d="M -110 -18 C -84 -60 -20 -104 -19 -185 C -17 -282 -39 -398 -61 -490 L 61 -490 C 39 -398 17 -282 19 -185 C 20 -104 84 -60 110 -18 L 81 -24 C 54 -76 10 -114 9 -184 C 8 -293 24 -406 33 -490 L -33 -490 C -24 -406 -8 -293 -9 -184 C -10 -114 -54 -76 -81 -24 Z" fill="url(#bh-jet-light)" opacity="0.72"/>
  <path d="M -5 -134 C -13 -195 -8 -239 -8 -304 L -19 -478 L 19 -478 L 8 -304 C 8 -239 13 -195 5 -134 Z" fill="url(#bh-jet-light)"/>
  <path d="M 0 -151 C -4 -229 3 -290 0 -439" fill="none" stroke="url(#bh-jet-light)" stroke-width="2.1"/>
  {jet_field_lines(colors)}
</g>
<ellipse rx="369" ry="83" fill="url(#bh-disk-halo)"/>
{disk_filaments(front=False)}
<circle r="175" fill="url(#bh-aureole)"/>
<circle id="event-horizon" r="92" fill="{dark}"><title>Apparent black-hole shadow, not the physical event-horizon radius</title></circle>
<g id="photon-rings">
  {lensed_disk()}
  <ellipse rx="99" ry="100" fill="none" stroke="url(#bh-lensed-light)" stroke-width="6.0" opacity="0.25"/>
  <ellipse id="photon-ring-main" rx="96" ry="97" fill="none" stroke="url(#bh-lensed-light)" stroke-width="2.2" opacity="0.93"/>
  <ellipse rx="94.3" ry="95.3" fill="none" stroke="{white}" stroke-width="0.65" opacity="0.52"/>
</g>
<path d="M -334 0 C -197 -10 -100 -11 0 -10 C 127 -10 208 -7 334 0 C 209 7 139 18 0 19 C -115 18 -235 7 -334 0 Z" fill="url(#bh-disk-light)" opacity="0.29"/>
{disk_filaments(front=True)}
<path d="M -332 0 Q 0 -9 332 0" fill="none" stroke="url(#bh-disk-light)" stroke-width="6.5" opacity="0.72"/>
<path d="M -317 -1 Q 0 -6 317 -1" fill="none" stroke="url(#bh-disk-light)" stroke-width="1.5"/>
</g>
'''
