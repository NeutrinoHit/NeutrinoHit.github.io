"""Neutrino Sky Atlas and its independently switchable antique-label layer.

PMNS parameters are illustrative, not a current fit. Geometry and probabilities
are computed; the hierarchy scales and other named sky objects are metaphors.
"""

from __future__ import annotations

import cmath
import math

from generate_series import esc, polyline_path
from neutrino_atlas_motifs import hierarchy, relics, anomaly_clouds, majorana_cluster, cp_bridge, bsm_portal


INKSCAPE = 'http://www.inkscape.org/namespaces/inkscape'
ATLAS_TOPICS = ('unitarity', 'oscillations', 'hierarchy', 'relics', 'anomalies', 'majorana', 'cp', 'bsm')


def pmns_matrix(parameters: dict) -> list[list[complex]]:
    s12, s13, s23 = (math.sqrt(parameters[f'sin2_theta{i}']) for i in (12, 13, 23))
    c12, c13, c23 = (math.sqrt(1 - parameters[f'sin2_theta{i}']) for i in (12, 13, 23))
    phase = cmath.exp(1j * math.radians(parameters['delta_cp_degrees']))
    return [
        [c12 * c13, s12 * c13, s13 * phase.conjugate()],
        [-s12 * c23 - c12 * s23 * s13 * phase,
         c12 * c23 - s12 * s23 * s13 * phase, s23 * c13],
        [s12 * s23 - c12 * c23 * s13 * phase,
         -c12 * s23 - s12 * c23 * s13 * phase, c23 * c13],
    ]


def unitarity_edges(parameters: dict) -> list[complex]:
    """Orthogonality of the first and third columns, in e/mu/tau order."""

    u = pmns_matrix(parameters)
    return [row[0] * row[2].conjugate() for row in u]


def triangle_points(parameters: dict, width: float) -> list[tuple[float, float]]:
    edges = unitarity_edges(parameters)
    assert abs(sum(edges)) < 1e-13
    # The normalization is a complex rotation and an isotropic scale only.
    # Keep the three angles of the physical triangle, not a generic icon.
    vertices = [0j, 1 + 0j, -edges[0] / edges[1]]
    real = [z.real for z in vertices]
    imag = [-z.imag for z in vertices]
    scale = width / (max(real) - min(real))
    return [((z.real - min(real)) * scale, (-z.imag - min(imag)) * scale)
            for z in vertices]


def oscillation_probabilities(parameters: dict, lovere: float) -> list[float]:
    """P(nu_mu -> nu_beta), vacuum, with L/E in km/GeV and dm^2 in eV^2."""

    u = pmns_matrix(parameters)
    dm2 = [0, parameters['dm21_sq_ev2'], parameters['dm31_sq_ev2']]
    probabilities = []
    for beta in range(3):
        amplitude = sum(u[beta][i] * u[1][i].conjugate()
                        * cmath.exp(-2j * 1.267 * dm2[i] * lovere)
                        for i in range(3))
        probabilities.append(abs(amplitude) ** 2)
    assert abs(sum(probabilities) - 1) < 1e-12
    return probabilities


def star(x: float, y: float, radius: float, color: str, opacity: float,
         cross: bool = False, extra: str = '') -> str:
    nodes = [
        f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{radius * 3:.3f}" '
        f'fill="url(#constellation-star-halo)" opacity="{opacity:.3f}"/>',
        f'<circle class="constellation-star" cx="{x:.3f}" cy="{y:.3f}" r="{radius:.3f}" '
        f'fill="{color}" opacity="{opacity:.3f}" {extra}/>',
    ]
    if cross:
        reach = radius * 2.7
        nodes.append(
            f'<path d="M {x - reach:.3f} {y:.3f} H {x + reach:.3f} '
            f'M {x:.3f} {y - reach:.3f} V {y + reach:.3f}" '
            f'fill="none" stroke="{color}" stroke-width="0.7" opacity="{opacity * .40:.3f}"/>'
        )
    return ''.join(nodes)


def place(config: dict) -> str:
    x, y = config['origin']
    return f'translate({x} {y}) rotate({config["angle"]}) scale({config.get("scale", 1)})'


def unitarity_asterism(config: dict, palette: dict) -> str:
    points = triangle_points(palette['pmns'], config['width'])
    nodes = [
        f'<path id="unitarity-triangle" d="{polyline_path(points)} Z" fill="none" '
        f'stroke="{palette["line_color"]}" stroke-width="1.05" opacity="0.46"/>',
    ]
    for i, (x, y) in enumerate(points):
        nodes.append(star(x, y, (3.2, 2.8, 3.5)[i], palette['star_color'], .88,
                          cross=i == 2, extra=f'data-vertex="{i}"'))
    for i, fraction in enumerate((.37, .61, .44)):
        p, q = points[i], points[(i + 1) % 3]
        x, y = (p[j] + fraction * (q[j] - p[j]) for j in (0, 1))
        nodes.append(star(x, y, 1.25, palette['star_color'], .52))
    return (f'<g id="constellation-unitarity" transform="{place(config)}">'
            '<title>Унитарность — замыкание лептонного треугольника</title>'
            + ''.join(nodes) + '</g>')


def oscillation_asterism(config: dict, palette: dict) -> str:
    samples = config['samples']
    flavor = config['flavor']
    points, stars = [], []
    for i in range(samples):
        t = i / (samples - 1)
        x = config['width'] * t
        # One decorative wave; brightness follows nu_mu survival probability.
        y = -22 * math.sin(math.tau * t)
        points.append((x, y))
        probability = oscillation_probabilities(palette['pmns'],
                      config['lovere_max_km_per_gev'] * t)[flavor]
        stars.append(star(x, y, 1.1 + 2.35 * math.sqrt(probability),
                          palette['star_color'], .32 + .56 * math.sqrt(probability),
                          extra=f'data-flavor="{flavor}" data-sample="{i}" data-probability="{probability:.12f}"'))
    wave = (f'<path id="oscillation-star-wave" d="{polyline_path(points)}" fill="none" '
            f'stroke="{palette["line_color"]}" stroke-width="0.95" opacity="0.34"/>')
    return (f'<g id="constellation-oscillations" transform="{place(config)}">'
            '<title>Oscillation Constellation — one wave of variable-brightness stars</title>'
            + wave + ''.join(stars) + '</g>')


def neutrino_constellations(colors: dict, labels_visible: bool | None = None) -> str:
    palette = colors['constellations']
    if labels_visible is None:
        labels_visible = palette['labels_visible']
    shapes = (unitarity_asterism(palette['unitarity'], palette)
              + oscillation_asterism(palette['oscillations'], palette))
    for key, render in [('hierarchy', hierarchy), ('relics', relics),
                        ('anomalies', anomaly_clouds), ('majorana', majorana_cluster),
                        ('cp', cp_bridge), ('bsm', bsm_portal)]:
        shapes += (f'<g id="constellation-{key}" transform="{place(palette[key])}">'
                   f'<title>{esc(palette[key]["name"])}</title>'
                   + render(palette, star) + '</g>')
    labels = []
    for key in ATLAS_TOPICS:
        item = palette[key]
        x, y = item['label']
        labels.append(
            f'<text x="{x}" y="{y}" transform="rotate({item["label_angle"]} {x} {y})" '
            f'text-anchor="middle" font-family="{esc(palette["label_font"])}" '
            f'font-style="italic" font-size="{palette["label_size"]}" letter-spacing="0.3" '
            f'fill="{palette["label_color"]}" opacity="{item.get("label_opacity", .76)}">{esc(item["name"])}</text>'
        )
    cx, cy = palette['atlas']['position']
    labels.append(f'''
<g id="neutrino-sky-atlas" fill="{palette['label_color']}" opacity="0.67">
  <text x="{cx}" y="{cy}" text-anchor="middle" font-family="{esc(palette['label_font'])}" font-style="italic" font-size="21">{esc(palette['atlas']['title'])}</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="{esc(palette['label_font'])}" font-size="11.5" letter-spacing="4.2">{esc(palette['atlas']['subtitle'])}</text>
  <path d="M {cx - 123} {cy - 6} H {cx - 77} M {cx + 77} {cy - 6} H {cx + 123}"
        fill="none" stroke="{palette['line_color']}" stroke-width="0.8" opacity="0.6"/>
  <path d="M {cx - 130} {cy - 6} l 3 -3 3 3 -3 3 Z M {cx + 124} {cy - 6} l 3 -3 3 3 -3 3 Z"/>
</g>''')
    return f'''
<g id="physics-constellations" xmlns:inkscape="{INKSCAPE}">
  <defs>
    <radialGradient id="constellation-star-halo">
      <stop offset="0" stop-color="{palette['star_color']}" stop-opacity="0.24"/>
      <stop offset="1" stop-color="{palette['star_color']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="atlas-relic-mist">
      <stop offset="0" stop-color="{palette['mist_color']}" stop-opacity="0.12"/>
      <stop offset="1" stop-color="{palette['mist_color']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="atlas-anomaly-mist">
      <stop offset="0" stop-color="{palette['portal_color']}" stop-opacity="0.17"/>
      <stop offset="1" stop-color="{palette['mist_color']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="atlas-portal-mist">
      <stop offset="0.12" stop-color="{palette['portal_color']}" stop-opacity="0"/>
      <stop offset="0.32" stop-color="{palette['portal_color']}" stop-opacity="0.20"/>
      <stop offset="1" stop-color="{palette['portal_color']}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <g id="constellation-figures" inkscape:groupmode="layer" inkscape:label="Физические созвездия">
    {shapes}
  </g>
  <g id="constellation-labels" inkscape:groupmode="layer" inkscape:label="Названия созвездий"
     style="display:{'inline' if labels_visible else 'none'}">
    {''.join(labels)}
  </g>
</g>
'''
