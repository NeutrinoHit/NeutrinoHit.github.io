"""Engraved-sky metaphors for neutrino topics, not observational sky maps."""

from __future__ import annotations

import math

from generate_series import polyline_path


def stroke(path: str, palette: dict, opacity: float = .35, width: float = 1.0) -> str:
    return (f'<path d="{path}" fill="none" stroke="{palette["line_color"]}" '
            f'stroke-width="{width}" stroke-linecap="round" opacity="{opacity}"/>')


def hierarchy(palette: dict, star) -> str:
    # Level scales do not favor either ordering. The pans hold two symbolic
    # triplets; horizontal offsets and vertical gaps are not measured values.
    nodes = [stroke('M -65 0 H 65 M 0 -13 V 80 M -21 84 L 0 73 L 21 84', palette, .44)]
    for x in (-65, 65):
        nodes.append(stroke(
            f'M {x} 0 L {x - 26} 42 M {x} 0 L {x + 26} 42 '
            f'M {x - 26} 42 Q {x} 68 {x + 26} 42', palette, .39))
    for x, y, r in [(-65, 0, 2.6), (65, 0, 2.6), (0, -13, 3.2), (0, 73, 2.1)]:
        nodes.append(star(x, y, r, palette['star_color'], .80, cross=x == 0 and y < 0))
    for ordering, points in {
        'normal': [(-70, 54), (-64, 49), (-64, 32)],
        'inverted': [(63, 37), (69, 32), (65, 54)],
    }.items():
        members = ''.join(star(x, y, 1.8, palette['star_color'], .75,
                        extra=f'data-mass-index="{i + 1}"')
                        for i, (x, y) in enumerate(points))
        nodes.append(f'<g id="mass-ordering-{ordering}">{members}</g>')
    return '<g id="hierarchy-scales">' + ''.join(nodes) + '</g>'


def relics(palette: dict, star) -> str:
    # A diffuse relic field, deliberately without an explosion center/shell.
    nodes = ['<ellipse rx="82" ry="47" fill="url(#atlas-relic-mist)" opacity="0.65"/>']
    for i in range(71):
        angle = i * 2.39996323
        radius = math.sqrt((i + .5) / 71)
        x = 71 * radius * math.cos(angle)
        y = 31 * radius * math.sin(angle) + 5 * math.sin(i * 1.7)
        r = .5 + .24 * (i % 4)
        nodes.append(star(x, y, r, palette['star_color'], .26 + .09 * (i % 4)))
    for x, y, r in [(-39, -11, 2), (25, 9, 2.2), (52, -18, 1.7)]:
        nodes.append(star(x, y, r, palette['star_color'], .61))
    return ''.join(nodes)


def anomaly_clouds(palette: dict, star) -> str:
    nodes = []
    for i, (cx, cy, rx, ry) in enumerate([(-39, 6, 60, 30), (24, -9, 52, 36), (48, 14, 48, 22)]):
        nodes.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                     'fill="url(#atlas-anomaly-mist)" opacity="0.55"/>')
        for shell in (0.77, 1.0):
            points = []
            for j in range(65):
                t = math.tau * j / 64
                ripple = 1 + .12 * math.sin(5 * t + i) + .08 * math.cos(3 * t - i)
                points.append((cx + shell * rx * ripple * math.cos(t),
                               cy + shell * ry * ripple * math.sin(t)))
            nodes.append(stroke(polyline_path(points) + ' Z', palette, .13, .85))
    for i in range(39):
        t = i * 2.39996323
        r = math.sqrt((i + 1) / 39)
        nodes.append(star(86 * r * math.cos(t), 34 * r * math.sin(t),
                          .65 + .24 * (i % 3), palette['star_color'], .25 + .06 * (i % 4)))
    return ''.join(nodes)


def majorana_cluster(palette: dict, star) -> str:
    # Conjugate-looking lobes share one center: a metaphor for self-conjugacy,
    # not a claim that the Majorana nature has been experimentally established.
    points = [(17, -30), (37, -16), (30, 21), (12, 31)]
    nodes = []
    for sign in (-1, 1):
        lobe = [(0, 0)] + [(sign * x, sign * y) for x, y in points] + [(0, 0)]
        nodes.append(stroke(polyline_path(lobe), palette, .27, .9))
        for i, (x, y) in enumerate(lobe[1:-1]):
            nodes.append(star(x, y, 1.75 + .3 * (i % 2), palette['star_color'], .66))
    nodes.append(star(0, 0, 3.15, palette['star_color'], .84, cross=True))
    for x, y in [(-42, 17), (44, 9), (-13, -43), (5, 44), (-25, -9), (23, 2)]:
        nodes.append(star(x, y, .8, palette['star_color'], .34))
    return ''.join(nodes)


def cp_bridge(palette: dict, star) -> str:
    # Two mirrored shores; a small open center denotes a question, not a
    # measured CP asymmetry or a literal representation of charge conjugation.
    nodes = [
        stroke('M -61 21 L -45 -13 C -32 -29 -19 -36 -6 -37 '
               'M 6 -37 C 19 -36 32 -29 45 -13 L 61 21', palette, .37),
        stroke('M -61 21 H -5 M 5 21 H 61 M -45 -13 V 21 M 45 -13 V 21 '
               'M -25 -30 V 21 M 25 -30 V 21', palette, .21, .85),
    ]
    for x, y, r in [(-61, 21, 2.35), (-45, -13, 2.05), (-25, -30, 1.65),
                    (25, -30, 1.65), (45, -13, 2.05), (61, 21, 2.35)]:
        nodes.append(star(x, y, r, palette['star_color'], .71))
    return ''.join(nodes)


def bsm_portal(palette: dict, star) -> str:
    nodes = ['<ellipse rx="58" ry="48" fill="url(#atlas-portal-mist)" opacity="0.5"/>']
    for arm in range(3):
        points = []
        for i in range(55):
            t = i / 54
            r = 9 + 37 * t ** 1.15
            angle = arm * math.tau / 3 + 1.12 * math.tau * t
            points.append((r * math.cos(angle), .73 * r * math.sin(angle)))
        nodes.append(stroke(polyline_path(points), palette, .17, .8))
        for i in (8, 20, 34, 51):
            x, y = points[i]
            nodes.append(star(x, y, 1 + i / 75, palette['portal_color'], .49))
    nodes.append('<circle r="8.0" fill="#03080F"/>')
    nodes.append(f'<ellipse rx="9.7" ry="7.2" fill="none" stroke="{palette["portal_color"]}" '
                 'stroke-width="1.0" opacity="0.48"/>')
    return ''.join(nodes)
