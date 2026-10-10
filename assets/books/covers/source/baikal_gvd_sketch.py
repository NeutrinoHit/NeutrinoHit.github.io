"""Unlabeled Baikal-GVD cluster and symbolic Cherenkov light for the cover."""

from __future__ import annotations

import math

from generate_series import polyline_path

LIGHT_VERTEX = (102.0, 319.0)
LIGHT_CENTER = (221.0, 180.0)


def light_axis_in_artwork(colors: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the signal origin and its unit axis in the shared artwork frame."""

    scene = colors['composition']
    x, y = scene['telescope_origin']
    scale = scene['telescope_scale']
    dx, dy = LIGHT_CENTER[0] - LIGHT_VERTEX[0], LIGHT_CENTER[1] - LIGHT_VERTEX[1]
    length = math.hypot(dx, dy)
    return ((x + scale * LIGHT_VERTEX[0], y + scale * LIGHT_VERTEX[1]),
            (dx / length, dy / length))


def cluster_positions() -> list[tuple[float, float]]:
    """One central string and seven peripheral strings at a radius of 60 m."""

    phase = 0.19
    return [(0.0, 0.0)] + [
        (60 * math.cos(phase + i * math.tau / 7),
         60 * math.sin(phase + i * math.tau / 7))
        for i in range(7)
    ]


def project(x: float, depth: float, height: float) -> tuple[float, float]:
    # The horizontal spacing is enlarged for legibility at book-cover scale.
    return 184 + 1.9 * x + 0.55 * depth, 369 + 0.28 * depth - 0.54 * height


def cone_geometry() -> tuple[tuple[float, float], list[tuple[float, float]]]:
    """Projected directional light envelope, with deliberately shortened width."""

    vertex = LIGHT_VERTEX
    center = LIGHT_CENTER
    dx, dy = center[0] - vertex[0], center[1] - vertex[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    theta_c = math.acos(1.0 / 1.34)  # illustrative water index, beta = 1
    radius = length * math.tan(theta_c) * 0.46
    rim = []
    for i in range(97):
        angle = math.tau * i / 96
        wide = radius * math.cos(angle)
        narrow = radius * 0.28 * math.sin(angle)
        rim.append((center[0] - uy * wide + ux * narrow,
                    center[1] + ux * wide + uy * narrow))
    return vertex, rim


def baikal_gvd_sketch(colors: dict) -> str:
    cable = colors["detector_cable"]
    glass = colors["detector_glass"]
    buoy = colors["detector_buoy"]
    light = colors["cherenkov_light"]
    white = colors["cherenkov_core"]
    vertex, rim = cone_geometry()
    cone_outline = polyline_path([vertex, *rim[:49]]) + " Z"
    rim_path = polyline_path(rim)

    background = f'''
<defs>
  <radialGradient id="gvd-water-glow">
    <stop offset="0" stop-color="{colors['detector_water']}" stop-opacity="0.55"/>
    <stop offset="0.65" stop-color="{colors['detector_water']}" stop-opacity="0.23"/>
    <stop offset="1" stop-color="{colors['detector_water']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="gvd-light-fill" gradientUnits="userSpaceOnUse" x1="102" y1="319" x2="221" y2="180">
    <stop offset="0" stop-color="{white}" stop-opacity="0.64"/>
    <stop offset="0.22" stop-color="{light}" stop-opacity="0.34"/>
    <stop offset="1" stop-color="{light}" stop-opacity="0.04"/>
  </linearGradient>
  <radialGradient id="gvd-hit-glow">
    <stop offset="0" stop-color="{white}" stop-opacity="0.93"/>
    <stop offset="0.20" stop-color="{light}" stop-opacity="0.76"/>
    <stop offset="0.52" stop-color="{light}" stop-opacity="0.20"/>
    <stop offset="1" stop-color="{light}" stop-opacity="0"/>
  </radialGradient>
</defs>
<ellipse cx="186" cy="231" rx="190" ry="232" fill="url(#gvd-water-glow)"/>
<g id="baikal-water-surface" fill="none" stroke="{cable}" stroke-linecap="round">
  <path d="M 24 25 C 77 17 119 29 168 23 S 267 15 349 24" stroke-width="1.2" opacity="0.52"/>
  <path d="M 56 31 C 109 25 153 36 199 30 S 290 22 325 29" stroke-width="0.7" opacity="0.26"/>
</g>
<path d="M 37 415 C 115 405 204 429 336 410" fill="none" stroke="{cable}" stroke-width="1.1" opacity="0.26"/>
'''

    string_layers: list[tuple[float, str]] = []
    hits = []
    for string_index, (x_world, depth) in enumerate(cluster_positions()):
        x, top_y = project(x_world, depth, 585)
        _, anchor_y = project(x_world, depth, -64)
        frontness = (depth + 60) / 120
        opacity = 0.44 + 0.48 * frontness
        nodes = [
            f'<path d="M {x:.2f} {top_y:.2f} V {anchor_y:.2f}" '
            f'fill="none" stroke="{cable}" stroke-width="1.1"/>',
            f'<path d="M {x:.2f} {top_y + 8:.2f} Q {x:.2f} 40 184 42" '
            f'fill="none" stroke="{cable}" stroke-width="0.7" opacity="0.35"/>',
            f'<path d="M {x - 4:.2f} {anchor_y:.2f} l -2 4 h 12 l -2 -4 z" '
            f'fill="{glass}" opacity="0.80"/>',
        ]
        for buoy_index in range(3):
            nodes.append(
                f'<ellipse cx="{x:.2f}" cy="{top_y + 3.9 * buoy_index:.2f}" '
                f'rx="3.2" ry="2.7" fill="{buoy}" opacity="0.90"/>'
            )
        for module_index in range(36):
            px, py = project(x_world, depth, 15 * module_index)
            nodes.append(
                f'<g class="gvd-optical-module">'
                f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.55" '
                f'fill="{colors["paper"]}" stroke="{glass}" stroke-width="0.95"/>'
                f'<path d="M {px - 1.8:.2f} {py + 0.3:.2f} '
                f'Q {px:.2f} {py + 3.3:.2f} {px + 1.8:.2f} {py + 0.3:.2f}" '
                f'fill="{glass}" opacity="0.75"/></g>'
            )
            # Stylized hit pattern around the directional light envelope.
            # These intensities do not encode observed charge or arrival time.
            fraction = (LIGHT_VERTEX[1] - py) / (LIGHT_VERTEX[1] - LIGHT_CENTER[1])
            axis_x = LIGHT_VERTEX[0] + (LIGHT_CENTER[0] - LIGHT_VERTEX[0]) * fraction
            distance = abs(px - axis_x)
            envelope = 10 + 50 * fraction
            strength = max(0.0, 1 - distance / max(1.0, envelope))
            if 0.10 < fraction < 1.1 and strength > 0.40:
                radius = 7.5 + strength * 5.0
                hits.append(
                    f'<g class="gvd-illuminated-module" opacity="{0.50 + 0.45 * strength:.3f}">'
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{radius:.2f}" fill="url(#gvd-hit-glow)"/>'
                    f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.8" fill="{light}"/>'
                    f'<circle cx="{px - 0.5:.2f}" cy="{py - 0.5:.2f}" r="1.1" fill="{white}"/></g>'
                )
        string_layers.append((depth,
            f'<g id="gvd-string-{string_index}" opacity="{opacity:.3f}">'
            + "".join(nodes) + "</g>"))

    cone = [
        f'<g id="cherenkov-light-cone">',
        f'<path d="{cone_outline}" fill="url(#gvd-light-fill)"/>',
        f'<path d="{rim_path}" fill="none" stroke="{light}" stroke-width="1.3" opacity="0.50"/>',
    ]
    for i in (0, 8, 16, 32, 40, 48):
        px, py = rim[i]
        opacity = 0.58 if i in (0, 48) else 0.15
        cone.append(
            f'<path d="M {vertex[0]} {vertex[1]} L {px:.2f} {py:.2f}" '
            f'fill="none" stroke="{light}" stroke-width="1.3" opacity="{opacity}"/>'
        )
    for fraction in (0.48, 0.76):
        points = [(vertex[0] + fraction * (x - vertex[0]),
                   vertex[1] + fraction * (y - vertex[1])) for x, y in rim]
        cone.append(
            f'<path d="{polyline_path(points)}" fill="none" stroke="{light}" '
            f'stroke-width="0.8" opacity="0.22"/>'
        )
    cone.extend([
        f'<circle cx="{vertex[0]}" cy="{vertex[1]}" r="18" fill="url(#gvd-hit-glow)"/>',
        f'<circle cx="{vertex[0]}" cy="{vertex[1]}" r="2.2" fill="{white}"/>',
        "</g>",
    ])
    rear = "".join(node for depth, node in sorted(string_layers) if depth < 0)
    front = "".join(node for depth, node in sorted(string_layers) if depth >= 0)
    scene = colors['composition']
    origin_x, origin_y = scene['telescope_origin']
    return (
        f'<g id="baikal-gvd-telescope" transform="translate({origin_x} {origin_y}) scale({scene["telescope_scale"]})">'
        + background + rear + "".join(cone) + front
        + '<g id="gvd-light-response">' + "".join(hits) + '</g></g>'
    )
