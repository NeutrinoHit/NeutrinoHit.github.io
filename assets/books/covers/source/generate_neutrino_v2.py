#!/usr/bin/env python3
"""Generate the current vector cover for the neutrino-physics textbook."""

from __future__ import annotations

import json
import math
from pathlib import Path

from baikal_gvd_sketch import baikal_gvd_sketch, light_axis_in_artwork
from black_hole_sketch import black_hole_sketch
from generate_series import nested_svg, svg_document
from generate_statistical_v2 import front_cover_v2, overview_v2, spread_v2
from neutrino_editorial_back import editorial_back
from neutrino_constellations import neutrino_constellations


ROOT = Path(__file__).resolve().parents[1]
SERIES_CONFIG = ROOT / 'config/series.json'
V2_CONFIG = ROOT / 'config/neutrino_v2.json'
BACK_CONFIG = ROOT / 'config/neutrino_back.json'
OUTPUT = ROOT / 'svg/v2'
ARTWORK_OUTPUT = OUTPUT / 'artwork'


def artwork_star_field(colors: dict) -> str:
    """Create a deterministic star field without embedding a raster texture."""

    nodes = []
    for index in range(112):
        x = 18 + ((index * 137 + index * index * 29 + 71) % 964)
        y = 17 + ((index * 211 + index * index * 13 + 43) % 895)
        radius = 0.65 + 0.30 * (index % 5)
        opacity = 0.20 + 0.105 * (index % 6)
        color = colors['star_cool'] if index % 9 == 0 else colors['star']
        nodes.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
            f'fill="{color}" opacity="{opacity:.3f}"/>'
        )
        if index % 31 == 0:
            nodes.append(
                f'<path d="M {x - 5:.2f} {y:.2f} H {x + 5:.2f} '
                f'M {x:.2f} {y - 5:.2f} V {y + 5:.2f}" '
                f'fill="none" stroke="{color}" stroke-width="0.9" opacity="0.54"/>'
            )
    return f'<g id="star-field">{"".join(nodes)}</g>'


def source_placement(colors: dict) -> tuple[float, float, float]:
    """Share the signal's editorial diagonal without drawing a connecting ray."""

    vertex, axis = light_axis_in_artwork(colors)
    distance = colors['composition']['source_to_signal_distance']
    angle = math.degrees(math.atan2(axis[0], -axis[1]))
    return vertex[0] - distance * axis[0], vertex[1] - distance * axis[1], angle


def neutrino_artwork_v2(colors: dict, labels_visible: bool | None = None) -> str:
    x, y, angle = source_placement(colors)
    engine = black_hole_sketch(colors, x, y, angle,
                              colors['composition']['black_hole_scale'])
    content = (
        f'<rect width="1000" height="930" fill="{colors["paper"]}"/>'
        + artwork_star_field(colors) + neutrino_constellations(colors, labels_visible)
        + engine + baikal_gvd_sketch(colors)
    )
    return svg_document(
        content, width=1000, height=930,
        title='Космический источник и Байкальский нейтринный телескоп',
        description='Neutrino Sky Atlas: линзированная чёрная дыра, джет и Байкал-GVD среди восьми физических созвездий и небесных пасхалок. Английские названия в стиле старинной карты, одна осцилляционная волна, весы иерархии, реликты, облака аномалий, кластер Майораны, CP-мост и скрытый BSM-портал.',
        metadata='Conceptual composition, not a measured event, Kerr ray tracing, or a real sky map. The black disk represents the apparent shadow. Jet emission is exterior to the shadow. The shared source/signal diagonal is editorial, not a source association. Baikal-GVD has eight strings of 36 modules; light denotes charged-secondary radiation. Unitarity uses a computed PMNS triangle; one star wave maps the vacuum nu_mu survival probability to radii and opacity. PMNS parameters are illustrative, not a current fit. Level hierarchy scales hold symbolic normal/inverted triplets. Relics, anomaly clouds, Majorana cluster, CP bridge and BSM portal are metaphors, not measured signals or established discoveries. The portal does not depict a physical observable singularity or a unique BSM model. English atlas labels and the cartouche are independently hideable.',
    )


def main() -> None:
    series = json.loads(SERIES_CONFIG.read_text(encoding='utf-8'))
    colors = json.loads(V2_CONFIG.read_text(encoding='utf-8'))
    copy = json.loads(BACK_CONFIG.read_text(encoding='utf-8'))
    book = next(book for book in series['books'] if book['slug'] == 'neutrino_physics')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ARTWORK_OUTPUT.mkdir(parents=True, exist_ok=True)

    artwork = neutrino_artwork_v2(colors)
    front = front_cover_v2(book, series, colors, artwork)
    back = editorial_back(copy, colors)
    labeled = front_cover_v2(book, series, colors, neutrino_artwork_v2(colors, True))
    unlabeled = front_cover_v2(book, series, colors, neutrino_artwork_v2(colors, False))
    variants = OUTPUT / 'variants'
    variants.mkdir(parents=True, exist_ok=True)
    comparison = svg_document(
        '<rect width="449" height="333" fill="#E4E8E5"/>'
        '<g fill="#183038" font-family="PT Serif" font-size="6.5">'
        '<text x="20" y="17">С названиями</text>'
        '<text x="239" y="17">Только созвездия</text></g>'
        + nested_svg(labeled, x=10, y=27, width=210, height=297, prefix='atlas_labeled')
        + nested_svg(unlabeled, x=229, y=27, width=210, height=297, prefix='atlas_unlabeled'),
        width=449, height=333,
        title='Созвездия нейтринной физики — два варианта лицевой обложки',
        description='Слева — Neutrino Sky Atlas с английскими названиями в стиле старинной карты, справа — те же фигуры без видимых подписей.',
        metadata='Both variants share identical geometry, typography and scientific parameters. Only visibility of the dedicated constellation-label layer differs.',
    )
    outputs = {
        ARTWORK_OUTPUT / 'neutrino_physics.svg': artwork,
        OUTPUT / 'neutrino_physics_front.svg': front,
        OUTPUT / 'neutrino_physics_back.svg': back,
        OUTPUT / 'neutrino_physics_spread_mockup.svg': spread_v2(front, back, book, series, colors),
        OUTPUT / 'neutrino_physics_overview.svg': overview_v2(front, back, book, series, colors),
        variants / 'neutrino_physics_front_labeled.svg': labeled,
        variants / 'neutrino_physics_front_unlabeled.svg': unlabeled,
        variants / 'neutrino_physics_constellations_comparison.svg': comparison,
    }
    for path, content in outputs.items():
        path.write_text(content, encoding='utf-8')
        print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
