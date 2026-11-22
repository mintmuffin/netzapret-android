"""Diplomacy (relations, alliances, guarantees, royal marriages) and AI."""
from __future__ import annotations

from typing import List, Optional

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


def offer_guarantee(world: World, guarantor: str, target: str) -> bool:
    """Guarantee a country's independence: if it is attacked, we join the war."""
    if guarantor == target:
        return False
    cg, ct = world.countries[guarantor], world.countries[target]
    if ct.relation(guarantor) < -40:
        return False
    cg.guarantees.add(target)
    ct.guaranteed_by.add(guarantor)
    world.add_log(f"Guarantee: {cg.name} guarantees independence of {ct.name}")
    return True


def royal_marriage(world: World, a: str, b: str) -> bool:
    """Dynastic tie between two countries' houses. Improves relations and can
    lead to a personal union if one side has no heir (ruling house dies out)."""
    ca, cb = world.countries[a], world.countries[b]
    if ca.house == cb.house:
        return False  # same house already
    if b in ca.royal_marriages:
        return False
    ca.royal_marriages.add(b)
    cb.royal_marriages.add(a)
    improve_relations(world, a, b, 15)
    world.add_log(f"Royal marriage: {ca.name} ({ca.house}) <-> {cb.name} ({cb.house})")
    return True


def check_personal_union(world: World) -> None:
    """If two countries share a ruling house via royal marriage and one is weak,
    the stronger may absorb the other into a personal union (vassalization)."""
    for tag, c in list(world.countries.items()):
        if not c.ai_enabled or c.player:
            continue
        for other_tag in list(c.royal_marriages):
            oc = world.countries.get(other_tag)
            if not oc or oc.house != c.house:
                continue
            # same house: weaker becomes vassal of stronger
            if c.manpower > oc.manpower * 1.5 and oc.manpower < 40:
                if other_tag not in c.vassals:
                    oc.vassal_of = c.tag
                    c.vassals.add(other_tag)
                    world.add_log(
                        f"Personal union: {oc.name} falls under {c.name} (house {c.house})"
                    )


def tick_ai(world: World) -> None:
    """Each AI country: relations, alliances, guarantees, royal marriages,
    wars, border claims and armies. Runs every AI_TICK days."""
    for tag, c in list(world.countries.items()):
        if not c.ai_enabled or c.player:
            continue
        _ai_relations(world, c)
        _ai_diplomacy(world, c)
        _ai_war_peace(world, c)
        _ai_borders(world, c)
        _ai_armies(world, c)
    check_personal_union(world)


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


def _ai_diplomacy(world: World, c: Country) -> None:
    """AI alliance / guarantee / royal marriage offers."""
    candidates = [
        (tag, oc) for tag, oc in world.countries.items()
        if tag != c.tag and not oc.ai_enabled == False
    ]
    # allies: befriend strong, same-religion neighbours
    for tag, oc in candidates:
        if tag in c.allies:
            continue
        rel = c.relation(tag)
        is_neighbour = any(
            world.regions[r].owner == tag
            for r, reg in world.regions.items() if reg.owner == c.tag
            for nb in world.adjacent_regions(r)
            if world.regions[nb].owner == tag
        )
        if (is_neighbour and rel > 40 and c.religion == oc.religion
                and world.rng.random() < 0.01):
            offer_alliance(world, c.tag, tag)
    # guarantees: protect small same-culture/religion neighbours from bullies
    for tag, oc in candidates:
        if tag in c.guarantees or tag in c.guaranteed_by:
            continue
        rel = c.relation(tag)
        if (rel > 50 and c.manpower > oc.manpower * 1.5
                and (c.religion == oc.religion or c.culture == oc.culture)
                and world.rng.random() < 0.008):
            offer_guarantee(world, c.tag, tag)
    # royal marriages: same religion, good relations
    for tag, oc in candidates:
        if tag in c.royal_marriages or oc.house == c.house:
            continue
        if c.relation(tag) > 60 and c.religion == oc.religion and world.rng.random() < 0.006:
            royal_marriage(world, c.tag, tag)


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
        # guaranteed targets are riskier
        guarantee_penalty = 20 if n in c.guaranteed_by else 0
        same_rel = 1 if c.religion == oc.religion else 0
        same_cult = 1 if c.culture == oc.culture else 0
        cb_bonus = 0
        if not same_cult and not same_rel:
            cb_bonus = 10  # holy war / ideology war cb available
        score = (power_ratio * 30 - rel - guarantee_penalty
                 + (1 - same_rel) * 8 + (1 - same_cult) * 6 + cb_bonus
                 + world.rng.uniform(-5, 5))
        if score > best_score:
            best_score = score
            best = n

    from war import start_war
    if best and best_score > 65 and c.treasury > 30 and world.rng.random() < 0.02:
        cb = "conquest"
        if c.religion != world.countries[best].religion:
            cb = "holy_war"
        elif c.ideology != world.countries[best].ideology:
            cb = "ideology_war"
        start_war(world, c.tag, best, cb)
        c.treasury -= 20


def _ai_borders(world: World, c: Country) -> None:
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
