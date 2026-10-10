"""Approved editorial copy and author credentials for the neutrino back cover."""

from __future__ import annotations

from pathlib import Path

from generate_statistical_v2 import cover_star_field_v2
from generate_series import esc, nested_svg, svg_document, svg_lines
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath


ROOT = Path(__file__).resolve().parents[1]
METRICS = TextToPath()
BODY_FAMILY = 'Arial'
DISPLAY_FAMILY = 'PT Serif'


def text_width(text: str, family: str, size: float, weight: int = 400) -> float:
    font = FontProperties(family=family, size=size, weight=weight)
    return METRICS.get_text_width_height_descent(text, font, ismath=False)[0]


def wrap_paragraph(text: str, width: float, size: float) -> list[str]:
    lines, current = [], ''
    for word in text.split():
        trial = f'{current} {word}'.strip()
        if current and text_width(trial, BODY_FAMILY, size) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    assert all(text_width(line, BODY_FAMILY, size) <= width for line in lines)
    return lines


def editorial_back(copy: dict, colors: dict) -> str:
    x, width = 22.0, 151.0
    headline = svg_lines(
        copy['headline_lines'], x=x, y=48, size=10.3, leading=12.4,
        family=DISPLAY_FAMILY, fill=colors['ink'], weight=400,
        letter_spacing=-0.1,
    )
    for line in copy['headline_lines']:
        assert text_width(line, DISPLAY_FAMILY, 10.3) < width

    blocks = []
    y = 100.0
    for paragraph in copy['paragraphs']:
        lines = wrap_paragraph(paragraph, width, 3.9)
        blocks.append(svg_lines(
            lines, x=x, y=y, size=3.9, leading=6.1,
            family=BODY_FAMILY, fill=colors['ink'],
        ))
        y += 6.1 * len(lines) + 3.1
    assert y < 191, f'Body extends into the audience line: {y}'

    bio_lines = wrap_paragraph(copy['author_description'], width, 3.25)
    assert len(bio_lines) <= 3, 'Author credentials extend into the award block'
    bio = svg_lines(bio_lines, x=x, y=220, size=3.25, leading=4.8,
                    family=BODY_FAMILY, fill=colors['subtle'])
    awards = []
    assert len(copy['awards']) <= 2
    for i, (year, award) in enumerate(copy['awards']):
        assert text_width(award, BODY_FAMILY, 3.3) < width - 15
        baseline = 246.0 + i * 6.5
        awards.append(
            f'<text x="22" y="{baseline}" font-family="{BODY_FAMILY}" '
            f'font-size="3.15" fill="{colors["disk_hot"]}">{esc(year)}</text>'
            f'<text x="37" y="{baseline}" font-family="{BODY_FAMILY}" '
            f'font-size="3.3" fill="{colors["ink"]}">{esc(award)}</text>'
        )
    assert text_width(copy['awards_qualification'], BODY_FAMILY, 3.1) < width

    logo = (ROOT / 'source/brand/neutrinohit_logo.svg').read_text(encoding='utf-8')
    # Preserve the original geometry; the cream/ink inverse needs no backplate.
    logo = logo.replace('"#000"', f'"{colors["ink"]}"')
    logo = logo.replace('"#fff"', f'"{colors["paper"]}"')
    logo_node = nested_svg(logo, x=22, y=266, width=16.5, height=16.5,
                          prefix='neutrino_editorial_back_logo')
    content = f'''
<rect width="210" height="297" fill="{colors['paper']}"/>
{cover_star_field_v2(colors, 'back')}
<rect x="190" y="0" width="20" height="297" fill="{colors['series_teal']}"/>
<rect x="187.4" y="0" width="2.6" height="297" fill="{colors['accent']}"/>
{headline}
<path d="M 22 88 H 43" stroke="{colors['disk_hot']}" stroke-width="0.6"/>
<g id="editorial-blurb">{''.join(blocks)}</g>
<text x="22" y="191" font-family="{BODY_FAMILY}" font-size="3.0" fill="{colors['subtle']}">{esc(copy['audience'])}</text>
<line x1="22" y1="201" x2="173" y2="201" stroke="{colors['hair']}" stroke-width="0.35"/>
<g id="author-credentials">
  <text x="22" y="212" font-family="{DISPLAY_FAMILY}" font-size="5.2" fill="{colors['ink']}">{esc(copy['author_name'])}</text>
  {bio}
  <text x="22" y="237" font-family="{BODY_FAMILY}" font-size="3.1" fill="{colors['subtle']}">{esc(copy['awards_qualification'])}</text>
  <g id="author-awards">{''.join(awards)}</g>
</g>
{logo_node}
<text x="44" y="273.5" font-family="{BODY_FAMILY}" font-size="3.15" font-weight="700" letter-spacing="0.45" fill="{colors['accent']}">NEUTRINOHIT</text>
<text x="44" y="279.5" font-family="{BODY_FAMILY}" font-size="2.6" fill="{colors['subtle']}">neutrinohit.github.io</text>
'''
    print(f'Neutrino back: body region ends at {y:.1f} mm; author bio {len(bio_lines)} lines')
    return svg_document(
        content, width=210, height=297,
        title='Введение в физику нейтрино — задняя обложка',
        description='Цельная аннотация, авторский блок с регалиями и международными наградами, светлый логотип NeutrinoHit.',
        metadata='Working A4 format with live text. The copy describes the planned complete book of 35 chapters in 10 parts. Both international awards are attributed to the author as a member of the Daya Bay collaboration. Credentials checked against the author CV and official JINR profile.',
    )
