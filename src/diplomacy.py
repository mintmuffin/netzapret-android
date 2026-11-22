"""Diplomacy (relations, alliances) and the autonomous country AI."""
from __future__ import annotations

from typing import List

from core import clamp
from world import Country, World


def improve_relations(world: World, a: str, b: str, amount: float = 1.0) -> None:
    ca, cb = world.countries[a], world.countries[b]
    ca.relations[b] = clamp(ca.relations.get(b, 0) + amount, -100, 100)
    cb.relations[a] = clamp(cb.relations.get(a, 0) + amount, -100, 100)


def damage_relations(world: World, a: str, b: str, amount: float) -> None:
    improve_relations(world, a, b, -amount)


def offer_alliance(world: World, a: str, b: str) -> bool:
    ca, cb = world.countries[a], world.countries[b]
    if cb.relation(a) < -30:
        return False
    ca.allies.add(b)
    cb.allies.add(a)
    world.add_log(f"Alliance: {ca.name} and {cb.name}")
    return True


def tick_ai(world: World) -> None:
    """Each AI country: manage relations, alliances, wars, border claims and
    armies. Runs every AI_TICK days."""
    for tag, c in list(world.countries.items()):
        if not c.ai_enabled or c.player:
            continue
        _ai_relations(world, c)
        _ai_war_peace(world, c)
        _ai_borders(world, c)
        _ai_armies(world, c)


def _ai_relations(world: World, c: Country) -> None:
    for tag, other in world.countries.items():
        if tag == c.tag:
            continue
        rel = c.relation(tag)
        if rel > 0:
            c.relations[tag] = max(0, rel - 0.02)
        elif rel < 0:
            c.relations[tag] = min(0, rel + 0.02)
        if c.religion == other.religion:
            c.relations[tag] = min(100, rel + 0.05)
        if c.culture == other.culture:
            c.relations[tag] = min(100, rel + 0.05)
        for w in world.wars.values():
            if w.active and ((w.attacker == c.tag and w.defender == tag) or
                             (w.defender == c.tag and w.attacker == tag)):
                c.relations[tag] = -100


def _ai_war_peace(world: World, c: Country) -> None:
    neighbours: List[str] = []
    for rid, reg in world.regions.items():
        if reg.owner == c.tag:
            for nb in world.adjacent_regions(rid):
                o = world.regions[nb].owner
                if o and o != c.tag:
                    neighbours.append(o)
    neighbours = list(set(neighbours))

    active_enemies = {w.defender if w.attacker == c.tag else w.attacker
                      for w in world.wars.values() if w.active
                      and (w.attacker == c.tag or w.defender == c.tag)}
    neighbours = [n for n in neighbours if n not in active_enemies]

    if not neighbours:
        return

    best = None
    best_score = -1e9
    for n in neighbours:
        oc = world.countries[n]
        power_ratio = c.manpower / max(oc.manpower, 1)
        rel = c.relation(n)
        same_rel = 1 if c.religion == oc.religion else 0
        score = power_ratio * 30 - rel + (1 - same_rel) * 10 + world.rng.uniform(-5, 5)
        if score > best_score:
            best_score = score
            best = n

    if best and best_score > 60 and c.treasury > 30 and world.rng.random() < 0.02:
        from war import start_war
        start_war(world, c.tag, best, "conquest")
        c.treasury -= 20


def _ai_borders(world: World, c: Country) -> None:
    # occasionally claim a neighbouring region of same culture/religion or a weak owner
    candidates = []
    for rid, reg in world.regions.items():
        if reg.owner == c.tag:
            for nb in world.adjacent_regions(rid):
                nreg = world.regions[nb]
                if nreg.owner and nreg.owner != c.tag:
                    oc = world.countries[nreg.owner]
                    same_cult = c.culture == oc.culture
                    weak = oc.manpower < c.manpower
                    hated = c.relation(nreg.owner) < -30
                    if same_cult or weak or hated:
                        candidates.append((nb, nreg.owner))
    if candidates and world.rng.random() < 0.015:
        rid, old = world.rng.choice(candidates)
        from influence import set_region_owner
        set_region_owner(world, rid, c.tag)
        damage_relations(world, c.tag, old, 5)


def _ai_armies(world: World, c: Country) -> None:
    my_armies = [a for a in world.armies if a.country == c.tag]
    for a in my_armies:
        if a.strength < 60 and c.manpower > 10:
            a.strength = min(80, a.strength + 0.5)
            c.manpower -= 0.1
    if (len(my_armies) < 3 and c.treasury > 80 and world.rng.random() < 0.005
            and not any(w.active for w in world.wars.values()
                        if w.attacker == c.tag or w.defender == c.tag)):
        if c.capital is not None:
            from world import Army
            reg = world.regions[c.capital]
            aid = len(world.armies) + 1
            world.armies.append(Army(id=aid, country=c.tag, region=c.capital,
                                     x=float(reg.center[0]), y=float(reg.center[1]),
                                     strength=world.rng.uniform(30, 60)))
            c.treasury -= 40
