"""Gradual influence spread (religion / culture / ideology / house) across
continuous fields, plus dynamic border computation from ownership."""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from core import MAP_H, MAP_W
from world import Country, Region, World


def spread_influence(world: World) -> None:
    """Each region projects its dominant factors into neighbouring regions.
    Mixes shift gradually, producing fuzzy, moving frontiers instead of
    hard province-locked borders."""
    for reg in world.regions.values():
        if reg.owner is None:
            continue
        c = world.country_obj(reg.owner)
        if c is None:
            continue
        for nb_id in world.adjacent_regions(reg.rid):
            nb = world.regions[nb_id]
            _pull(nb, reg, c)

    _normalise_all(world.regions.values())


def _pull(target: Region, source: Region, country: Country) -> None:
    strength = 0.06
    factors = ("religion", "culture", "ideology", "house")
    for kind in factors:
        src_map = getattr(source, kind)
        tgt_map = getattr(target, kind)
        if not src_map:
            continue
        dom = source.dominant(kind)
        if dom is None:
            continue
        weight = src_map[dom] * strength
        if target.owner == country.tag:
            weight *= 2.0
        tgt_map[dom] = tgt_map.get(dom, 0.0) + weight
        for k in list(tgt_map):
            if k != dom:
                tgt_map[k] *= 0.998


def _normalise_all(regions) -> None:
    for reg in regions:
        for attr in ("religion", "culture", "ideology", "house"):
            d = getattr(reg, attr)
            total = sum(d.values())
            if total > 0:
                for k in d:
                    d[k] /= total
            for k in [k for k, v in d.items() if v < 0.01]:
                del d[k]


def compute_border_lines(world: World) -> List[Tuple[float, float, float, float]]:
    """Line segments (x1, y1, x2, y2) in cell coords between adjacent regions
    with different owners. Rendered as the political border."""
    lines: List[Tuple[float, float, float, float]] = []
    seen: set = set()
    for rid, reg in world.regions.items():
        o1 = reg.owner
        if o1 is None:
            continue
        for cx, cy in reg.cells:
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                    nb = int(world.region_grid[ny, nx])
                    if nb != -1 and nb != rid:
                        pair = tuple(sorted((rid, nb)))
                        if pair in seen:
                            continue
                        seen.add(pair)
                        o2 = world.regions[nb].owner
                        if o2 is not None and o1 != o2:
                            lines.append((cx + 0.5 + dx * 0.5, cy + 0.5 + dy * 0.5,
                                          cx + 0.5 - dx * 0.5, cy + 0.5 - dy * 0.5))
    return lines


def set_region_owner(world: World, rid: int, tag: str) -> None:
    """Redraw a border: assign a region to a country. Influence mixes seed
    from the new owner over time."""
    reg = world.regions[rid]
    old = reg.owner
    reg.owner = tag
    c = world.country_obj(tag)
    if c:
        reg.religion = {c.religion: 1.0}
        reg.culture = {c.culture: 1.0}
        reg.ideology = {c.ideology: 1.0}
        reg.house = {c.house: 1.0}
    if old and old != tag:
        world.add_log(f"Border redrawn: region {rid} now {tag} (was {old})")
    elif tag:
        world.add_log(f"Region {rid} claimed by {tag}")


def dominant_factor_color(world: World, reg: Region, mode: str):
    """Color for rendering one region under a given map mode."""
    if mode == "political":
        if reg.owner:
            return world.countries[reg.owner].color
        return (60, 60, 70)

    if mode == "relations":
        sc = world.selected_country
        if not sc or not reg.owner:
            return (60, 60, 70)
        rel = world.countries[sc].relation(reg.owner)
        t = (rel + 100) / 200
        return _blend((200, 50, 50), (80, 200, 100), t)

    kind = {"religion": "religion", "culture": "culture",
            "ideology": "ideology", "house": "house"}.get(mode)
    if kind:
        factors = getattr(world, kind + "s")
        dom = reg.dominant(kind)
        if dom and dom in factors:
            base = factors[dom].color
            strength = getattr(reg, kind).get(dom, 0.0)
            return _blend((255, 255, 255), base, strength)
        return (70, 70, 80)

    if mode == "terrain":
        return TERRAIN_COLORS.get(reg.terrain, (90, 90, 100))
    return (100, 100, 110)


TERRAIN_COLORS = {
    "plains": (140, 170, 120),
    "hills": (130, 120, 90),
    "forest": (60, 130, 70),
    "mountains": (110, 100, 110),
    "desert": (210, 190, 130),
    "water": (70, 120, 180),
}


def _blend(c1, c2, t):
    from core import lerp
    t = max(0.0, min(1.0, t))
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))
