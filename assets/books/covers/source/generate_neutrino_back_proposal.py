#!/usr/bin/env python3
"""Re-export the adopted editorial design at the earlier proposal filenames."""

import json
from pathlib import Path

from generate_series import nested_svg, svg_document
from neutrino_editorial_back import editorial_back

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    copy = json.loads((ROOT / 'config/neutrino_back.json').read_text(encoding='utf-8'))
    colors = json.loads((ROOT / 'config/neutrino_v2.json').read_text(encoding='utf-8'))
    output = ROOT / 'svg/proposals'
    output.mkdir(parents=True, exist_ok=True)
    back = editorial_back(copy, colors)
    front = (ROOT / 'svg/v2/neutrino_physics_front.svg').read_text(encoding='utf-8')
    content = (
        '<rect width="449" height="317" fill="#D6DDDC"/>'
        + nested_svg(front, x=10, y=10, width=210, height=297, prefix='editorial_front')
        + nested_svg(back, x=229, y=10, width=210, height=297, prefix='editorial_back')
    )
    overview = svg_document(
        content, width=449, height=317,
        title='Нейтринная книга — лицевая сторона и редакционный оборот',
        description='Текущая композиция с линзированной чёрной дырой и Байкал-GVD; аннотация и регалии автора на обороте.',
        metadata='Editorial design adopted into the current v2 cover. These earlier proposal filenames remain available for existing links.',
    )
    for name, document in {
        'neutrino_physics_back_editorial.svg': back,
        'neutrino_physics_editorial_overview.svg': overview,
    }.items():
        path = output / name
        path.write_text(document, encoding='utf-8')
        print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
