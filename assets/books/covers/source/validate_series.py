#!/usr/bin/env python3
"""Structural checks for generated NeutrinoHit cover SVGs."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from baikal_gvd_sketch import light_axis_in_artwork
from neutrino_constellations import ATLAS_TOPICS, pmns_matrix, unitarity_edges, triangle_points, oscillation_probabilities

ROOT = Path(__file__).resolve().parents[1]
V1_OUTPUT = ROOT / "svg" / "v1"
V2_OUTPUT = ROOT / "svg" / "v2"
SLUGS = ["statistical_methods", "neutrino_physics", "particle_physics", "gravity"]
V2_SLUGS = ["statistical_methods", "neutrino_physics"]


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def check_svg(path: Path) -> list[str]:
    errors = []
    raw = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        return [f"invalid XML: {error}"]

    if local_name(root.tag) != "svg":
        errors.append("root element is not svg")
    if not any(local_name(node.tag) == "metadata" for node in root.iter()):
        errors.append("missing metadata")
    if any(local_name(node.tag) == "image" for node in root.iter()):
        errors.append("contains raster image element")
    if "data:image" in raw or "/mnt/data" in raw:
        errors.append("contains embedded image data or a non-portable /mnt/data path")

    ids = re.findall(r'\bid="([^"]+)"', raw)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append(f"duplicate ids: {', '.join(duplicates[:6])}")

    external_hrefs = [
        value
        for value in re.findall(r'(?:href|xlink:href)="([^"]+)"', raw)
        if not value.startswith("#")
    ]
    if external_hrefs:
        errors.append(f"external hrefs: {', '.join(external_hrefs[:3])}")
    return errors


def check_constellations(root: ET.Element, colors: dict) -> list[str]:
    errors = []
    settings = colors['constellations']
    parameters = settings['pmns']
    u = pmns_matrix(parameters)
    for a in range(3):
        for b in range(3):
            inner = sum(u[a][i] * u[b][i].conjugate() for i in range(3))
            if abs(inner - int(a == b)) > 1e-13:
                errors.append('PMNS matrix is not unitary')
    if abs(sum(unitarity_edges(parameters))) > 1e-13:
        errors.append('leptonic triangle does not close')

    ids = {node.get('id'): node for node in root.iter() if node.get('id')}
    triangle = ids.get('constellation-unitarity')
    actual = {} if triangle is None else {
        int(node.get('data-vertex')): (float(node.get('cx')), float(node.get('cy')))
        for node in triangle.iter() if node.get('data-vertex') is not None
    }
    points = triangle_points(parameters, settings['unitarity']['width'])
    if len(actual) != 3 or any(
        i not in actual or math.dist(actual[i], point) > .001
        for i, point in enumerate(points)
    ):
        errors.append('rendered triangle vertices differ from the PMNS construction')

    stars = [node for node in root.iter() if node.get('data-probability') is not None]
    count = settings['oscillations']['samples']
    selected_flavor = settings['oscillations']['flavor']
    if len(stars) != count:
        errors.append('expected exactly one star wave, not three flavor waves')
    for i in range(count):
        sample = [node for node in stars if node.get('data-sample') == str(i)]
        if len(sample) != 1 or sample[0].get('data-flavor') != str(selected_flavor):
            errors.append(f'incorrect single-wave sample {i}')
            continue
        probabilities = oscillation_probabilities(parameters,
            settings['oscillations']['lovere_max_km_per_gev'] * i / (count - 1))
        if abs(sum(probabilities) - 1) > 2e-12:
            errors.append(f'flavor probabilities do not sum to unity at sample {i}')
        for node in sample:
            probability = probabilities[int(node.get('data-flavor'))]
            if abs(float(node.get('data-probability')) - probability) > 1e-12:
                errors.append(f'incorrect flavor probability at sample {i}')
            if abs(float(node.get('r')) - (1.1 + 2.35 * math.sqrt(probability))) > .00051:
                errors.append(f'incorrect probability-to-radius map at sample {i}')

    for ordering in ('normal', 'inverted'):
        group = ids.get(f'mass-ordering-{ordering}')
        positions = {} if group is None else {
            int(node.get('data-mass-index')): float(node.get('cy'))
            for node in group.iter() if node.get('data-mass-index') is not None
        }
        if set(positions) != {1, 2, 3}:
            errors.append(f'incomplete {ordering} mass triplet')
        else:
            sequence = sorted(positions, key=positions.get, reverse=True)
            if sequence != ([1, 2, 3] if ordering == 'normal' else [3, 1, 2]):
                errors.append(f'incorrect {ordering} mass ordering')

    labels = ids.get('constellation-labels')
    if labels is None or labels.get('{http://www.inkscape.org/namespaces/inkscape}groupmode') != 'layer':
        errors.append('atlas labels are not an independently switchable editor layer')
    elif labels.get('style') != f'display:{"inline" if settings["labels_visible"] else "none"}':
        errors.append('atlas label visibility differs from the configuration')
    for key in ATLAS_TOPICS:
        if f'constellation-{key}' not in ids:
            errors.append(f'missing atlas object: {key}')
    for key in ('oscillation-star-wave', 'hierarchy-scales', 'neutrino-sky-atlas'):
        if key not in ids:
            errors.append(f'missing atlas feature: {key}')
    if any(key.startswith('constellation-flavor-') for key in ids):
        errors.append('obsolete three-wave oscillation motif is present')
    return errors


def main() -> None:
    expected = {V1_OUTPUT / "series_overview.svg"}
    expected.update({
        ROOT / 'svg/proposals/neutrino_physics_back_editorial.svg',
        ROOT / 'svg/proposals/neutrino_physics_editorial_overview.svg',
        V2_OUTPUT / 'variants/neutrino_physics_front_labeled.svg',
        V2_OUTPUT / 'variants/neutrino_physics_front_unlabeled.svg',
        V2_OUTPUT / 'variants/neutrino_physics_constellations_comparison.svg',
    })
    expected.update(V1_OUTPUT / "artwork" / f"{slug}.svg" for slug in SLUGS)
    for slug in SLUGS:
        expected.update(
            {
                V1_OUTPUT / f"{slug}_front.svg",
                V1_OUTPUT / f"{slug}_back.svg",
                V1_OUTPUT / f"{slug}_spread_mockup.svg",
            }
        )
    for slug in V2_SLUGS:
        expected.update(
            {
                V2_OUTPUT / "artwork" / f"{slug}.svg",
                V2_OUTPUT / f"{slug}_front.svg",
                V2_OUTPUT / f"{slug}_back.svg",
                V2_OUTPUT / f"{slug}_spread_mockup.svg",
                V2_OUTPUT / f"{slug}_overview.svg",
            }
        )

    failures = []
    for path in sorted(expected):
        if not path.exists():
            failures.append(f"{path.relative_to(ROOT)}: missing")
            continue
        errors = check_svg(path)
        for error in errors:
            failures.append(f"{path.relative_to(ROOT)}: {error}")

    for slug in SLUGS:
        for side in ("front", "back"):
            path = V1_OUTPUT / f"{slug}_{side}.svg"
            if path.exists():
                root = ET.parse(path).getroot()
                if root.attrib.get("viewBox") != "0 0 210 297":
                    failures.append(f"{path.relative_to(ROOT)}: expected A4 viewBox")

    for slug in V2_SLUGS:
        for side in ("front", "back"):
            path = V2_OUTPUT / f"{slug}_{side}.svg"
            if path.exists():
                root = ET.parse(path).getroot()
                if root.attrib.get("viewBox") != "0 0 210 297":
                    failures.append(f"{path.relative_to(ROOT)}: expected A4 viewBox")

    ordinal_pattern = re.compile(r"\b0[1-4]\s*/\s*04\b")
    for path in sorted(expected):
        if path.exists() and ordinal_pattern.search(path.read_text(encoding="utf-8")):
            failures.append(f"{path.relative_to(ROOT)}: contains a visible series ordinal")

    front_paths = [V1_OUTPUT / f"{slug}_front.svg" for slug in SLUGS]
    front_paths.extend(V2_OUTPUT / f"{slug}_front.svg" for slug in V2_SLUGS)
    for path in front_paths:
        if path.exists() and "NEUTRINOHIT" in path.read_text(encoding="utf-8"):
            failures.append(f"{path.relative_to(ROOT)}: contains the back-only wordmark")

    for slug in V2_SLUGS:
        v2_back = V2_OUTPUT / f"{slug}_back.svg"
        if v2_back.exists() and "NEUTRINOHIT" not in v2_back.read_text(encoding="utf-8"):
            failures.append(f"{v2_back.relative_to(ROOT)}: missing NeutrinoHit back branding")

    v2_artwork = V2_OUTPUT / "artwork" / "statistical_methods.svg"
    if v2_artwork.exists():
        raw = v2_artwork.read_text(encoding="utf-8")
        for required in (
            'id="profile-dm21"',
            'id="profile-s12"',
            'id="expected-noosc"',
            'id="expected-osc"',
            r"$q(\theta)$",
            r"$=-2\ln\lambda(\theta)$",
            r"$\lambda(\theta)$",
            r"$=\frac{L(\theta,\hat{\eta}(\theta))}{L(\hat{\theta},\hat{\eta})}$",
        ):
            if required not in raw:
                failures.append(
                    f"{v2_artwork.relative_to(ROOT)}: missing required vector element {required}"
                )
        if 'fill="white"' in raw or 'fill="#FFFFFF"' in raw:
            failures.append(f"{v2_artwork.relative_to(ROOT)}: contains a white background")

    neutrino_artwork = V2_OUTPUT / "artwork" / "neutrino_physics.svg"
    if neutrino_artwork.exists():
        raw = neutrino_artwork.read_text(encoding="utf-8")
        root = ET.fromstring(raw)
        colors = json.loads((ROOT / 'config/neutrino_v2.json').read_text())
        failures.extend(f'neutrino constellations: {error}' for error in check_constellations(root, colors))
        for required in (
            'id="black-hole-engine"',
            'id="event-horizon"',
            'id="relativistic-jet"',
            'id="star-field"',
            'id="photon-rings"',
            'id="photon-ring-main"',
            'id="jet-exterior-flow"',
            'id="bh-exterior-only"',
            'id="baikal-gvd-telescope"',
            'id="constellation-unitarity"',
            'id="constellation-oscillations"',
            'id="constellation-hierarchy"',
            'id="constellation-labels"',
        ):
            if required not in raw:
                failures.append(
                    f"{neutrino_artwork.relative_to(ROOT)}: missing required vector element {required}"
                )
        if 'fill="white"' in raw or 'fill="#FFFFFF"' in raw:
            failures.append(f"{neutrino_artwork.relative_to(ROOT)}: contains a white background")
        if any(
            forbidden in raw
            for forbidden in ("neutrino-track", "neutrino-v2-arrow", "quantum-chameleon")
        ):
            failures.append(f"{neutrino_artwork.relative_to(ROOT)}: contains a removed motif")
        by_id = {node.get('id'): node for node in root.iter() if node.get('id')}
        label_layer = by_id.get('constellation-labels')
        label_nodes = [] if label_layer is None else list(label_layer.iter())
        if any(local_name(node.tag) == 'text' and node not in label_nodes for node in root.iter()):
            failures.append('neutrino artwork: text label outside the dedicated atlas layer')
        names = [node.text for node in label_nodes if local_name(node.tag) == 'text']
        atlas = colors['constellations']
        expected_names = [atlas[key]['name'] for key in ATLAS_TOPICS]
        expected_names += [atlas['atlas']['title'], atlas['atlas']['subtitle']]
        if names != expected_names:
            failures.append('neutrino artwork: missing English atlas names or footer cartouche')
        modules = [node for node in root.iter() if node.get('class') == 'gvd-optical-module']
        strings = [key for key in by_id if re.fullmatch(r'gvd-string-\d+', key)]
        if len(strings) != 8 or len(modules) != 288:
            failures.append('neutrino artwork: expected eight strings and 288 optical modules')

        engine = by_id.get('black-hole-engine')
        transform = engine.get('transform', '') if engine is not None else ''
        placement = re.fullmatch(r'translate\(([-\d.]+) ([-\d.]+)\) rotate\(([-\d.]+)\) scale\(([-\d.]+)\)', transform)
        if not placement:
            failures.append('neutrino artwork: missing source placement transform')
        else:
            x, y, angle, scale = map(float, placement.groups())
            colors = json.loads((ROOT / 'config/neutrino_v2.json').read_text())
            vertex, axis = light_axis_in_artwork(colors)
            dx, dy = vertex[0] - x, vertex[1] - y
            cross = dx * axis[1] - dy * axis[0]
            angle_rad = math.radians(angle)
            if abs(cross) > 1e-5 or not math.isclose(
                math.sin(angle_rad) * axis[0] - math.cos(angle_rad) * axis[1], 1, abs_tol=1e-9
            ):
                failures.append('neutrino artwork: source and signal are not on the same directed axis')
            if not math.isclose(math.hypot(dx, dy), colors['composition']['source_to_signal_distance'], abs_tol=1e-5):
                failures.append('neutrino artwork: source placement does not match its configuration')
            if not math.isclose(scale, colors['composition']['black_hole_scale']):
                failures.append('neutrino artwork: source scale does not match its configuration')

        exterior = by_id.get('jet-exterior-flow')
        mask = by_id.get('bh-exterior-only')
        shadow = by_id.get('event-horizon')
        cutouts = [] if mask is None else [n for n in mask if local_name(n.tag) == 'circle']
        if (exterior is None or exterior.get('mask') != 'url(#bh-exterior-only)'
                or shadow is None or not cutouts
                or float(cutouts[0].get('r', 0)) < float(shadow.get('r', 0))):
            failures.append('neutrino artwork: luminous flow is not excluded from the apparent shadow')

    back_path = V2_OUTPUT / 'neutrino_physics_back.svg'
    if back_path.exists():
        root = ET.parse(back_path).getroot()
        by_id = {node.get('id'): node for node in root.iter() if node.get('id')}
        copy = json.loads((ROOT / 'config/neutrino_back.json').read_text())
        blurb = by_id.get('editorial-blurb')
        actual = '' if blurb is None else ' '.join(' '.join(blurb.itertext()).split())
        if actual != ' '.join(copy['paragraphs']):
            failures.append('neutrino back: approved editorial copy is missing or altered')
        author = by_id.get('author-credentials')
        author_text = '' if author is None else ' '.join(' '.join(author.itertext()).split())
        required = [copy['author_name'], copy['author_description'], copy['awards_qualification']]
        required.extend(value for award in copy['awards'] for value in award)
        if any(value not in author_text for value in required):
            failures.append('neutrino back: author credentials or award attribution are missing')
        proposal_path = ROOT / 'svg/proposals/neutrino_physics_back_editorial.svg'
        if proposal_path.exists() and proposal_path.read_bytes() != back_path.read_bytes():
            failures.append('neutrino back: earlier editorial export is stale')

    variants = V2_OUTPUT / 'variants'
    labeled_path = variants / 'neutrino_physics_front_labeled.svg'
    unlabeled_path = variants / 'neutrino_physics_front_unlabeled.svg'
    if labeled_path.exists() and unlabeled_path.exists():
        labeled, unlabeled = labeled_path.read_text(), unlabeled_path.read_text()
        if labeled.replace('style="display:inline"', 'style="display:none"') != unlabeled:
            failures.append('constellation variants differ beyond label-layer visibility')
        if 'style="display:inline"' not in labeled or 'style="display:none"' not in unlabeled:
            failures.append('constellation variants do not have opposite label visibility')
        colors = json.loads((ROOT / 'config/neutrino_v2.json').read_text())
        canonical = labeled if colors['constellations']['labels_visible'] else unlabeled
        if (V2_OUTPUT / 'neutrino_physics_front.svg').read_text() != canonical:
            failures.append('canonical neutrino front differs from the configured atlas variant')

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"validated {len(expected)} SVG files: XML, IDs, vector-only content, and links")


if __name__ == "__main__":
    main()
