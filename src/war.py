"""Armies, frontlines, war score, occupation and peace treaties."""
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from core import clamp
from world import Army, Country, Front, War, World

# casus belli: name -> (war score multiplier, description)
CB_TABLE = {
    "conquest": (1.0, "Conquest"),
    "holy_war": (1.3, "Holy War"),
    "ideology_war": (1.2, "Ideology War"),
    "reconquest": (1.1, "Reconquest"),
}


def start_war(world: World, attacker: str, defender: str, cb: str = "conquest") -> Optional[str]:
    if attacker == defender:
        return None
    wid = f"w{len(world.wars) + 1}"
    war = War(id=wid, attacker=attacker, defender=defender, cb=cb, started=world.day_index)
    world.wars[wid] = war

    ca = world.country_obj(attacker)
    cd = world.country_obj(defender)
    if ca:
        ca.relations[defender] = clamp(ca.relations.get(defender, 0) - 40, -100, 100)
        ca.allies.discard(defender)
    if cd:
        cd.relations[attacker] = clamp(cd.relations.get(attacker, 0) - 40, -100, 100)
        cd.allies.discard(attacker)

    # allies join
    for tag, c in list(world.countries.items()):
        if tag in (attacker, defender) or not c.ai_enabled:
            continue
        if attacker in c.allies:
            _join_war(world, wid, tag, attacker_side=True)
        elif defender in c.allies:
            _join_war(world, wid, tag, attacker_side=False)
    # guarantees: guarantors of the defender join on defender's side
    if cd:
        for guarantor in list(cd.guaranteed_by):
            if guarantor not in (attacker, defender):
                gc = world.country_obj(guarantor)
                if gc and gc.ai_enabled:
                    _join_war(world, wid, guarantor, attacker_side=False)
                    # breaking a guarantee hurts relations with the aggressor
                    gc.relations[attacker] = clamp(gc.relations.get(attacker, 0) - 25, -100, 100)

    _make_fronts(world, war)
    cb_name = CB_TABLE.get(cb, ("conquest", "Conquest"))[1]
    world.add_log(f"WAR: {ca.name if ca else attacker} declares war on "
                  f"{cd.name if cd else defender} ({cb_name})")
    return wid


def _join_war(world: World, wid: str, tag: str, attacker_side: bool) -> None:
    war = world.wars[wid]
    c = world.country_obj(tag)
    if not c:
        return
    side = "attacker" if attacker_side else "defender"
    world.add_log(f"{c.name} joins the war on {side} side")


def _make_fronts(world: World, war: War) -> None:
    fid = f"f{war.id}"
    front = Front(id=fid, war=war.id, a=war.attacker, b=war.defender)
    pairs = world.border_region_pairs()
    for r1, r2 in pairs:
        o1 = world.regions[r1].owner
        o2 = world.regions[r2].owner
        if {o1, o2} == {war.attacker, war.defender}:
            front.regions.extend([r1, r2])
    if front.regions:
        world.fronts[fid] = front
        war.front_ids.append(fid)


def tick_armies(world: World) -> None:
    """Move armies, resolve frontline combat, handle occupation."""
    for army in list(world.armies):
        c = world.country_obj(army.country)
        if c is None:
            continue
        _tick_one_army(world, army, c)

    for war in world.wars.values():
        if not war.active:
            continue
        mult, _ = CB_TABLE.get(war.cb, CB_TABLE["conquest"])
        score = len(war.occupied) * 2.0 * mult
        score += sum(world.wars[war.id].battles_won.get(side, 0) * 1.5 * mult
                     for side in (war.attacker, war.defender))
        war.war_score = score


def _tick_one_army(world: World, army: Army, c: Country) -> None:
    reg = world.regions[army.region]
    enemy_wars = [w for w in world.wars.values()
                  if w.active and (w.attacker == army.country or w.defender == army.country)]
    if not enemy_wars:
        army.org = min(100, army.org + 0.5)
        return

    war = enemy_wars[0]
    enemy = war.defender if war.attacker == army.country else war.attacker

    if world.regions[army.region].owner == enemy:
        _assault_region(world, army, war, enemy, army.region)
        return

    targets = [r for r in world.adjacent_regions(army.region)
               if world.regions[r].owner == enemy]
    if not targets:
        _move_toward_enemy(world, army, enemy)
        return

    target = targets[0]
    army.target = target
    treg = world.regions[target]
    import math
    if math.hypot(treg.center[0] - army.x, treg.center[1] - army.y) < 1.5:
        army.region = target
        _assault_region(world, army, war, enemy, target)
    else:
        army.x += (treg.center[0] - army.x) * 0.1
        army.y += (treg.center[1] - army.y) * 0.1


def _assault_region(world: World, army: Army, war: War, enemy: str, rid: int) -> None:
    """Storm a garrison-held enemy region. Success -> military occupation."""
    reg = world.regions[rid]
    garrison = 20.0 + reg.fort * 15.0
    ea = army.strength * army.org / 100
    army.org -= 2.0
    if ea > garrison:
        margin = (ea - garrison) / max(ea, 1)
        world.wars[war.id].battles_won[army.country] = \
            world.wars[war.id].battles_won.get(army.country, 0) + 1
        army.strength *= (1 - 0.1 * margin)
        reg.controlled = True
        reg.occupier = army.country
        world.wars[war.id].occupied[rid] = army.country
        wc = world.country_obj(army.country)
        world.add_log(f"{wc.name if wc else army.country} occupies region {rid}")
    else:
        army.strength *= 0.85
        army.org -= 10
    if army.org <= 0 or army.strength <= 5:
        if army in world.armies:
            world.armies.remove(army)
        wc = world.country_obj(enemy)
        world.add_log(f"{wc.name if wc else enemy} army destroyed at region {rid}")


def _move_toward_enemy(world: World, army: Army, enemy: str) -> None:
    best = None
    best_d = 1e9
    for rid, reg in world.regions.items():
        if reg.owner == enemy:
            d = math_dist(army.x, army.y, reg.center[0], reg.center[1])
            if d < best_d:
                best_d = d
                best = rid
    if best is not None:
        army.target = best
        treg = world.regions[best]
        army.x += (treg.center[0] - army.x) * 0.05
        army.y += (treg.center[1] - army.y) * 0.05


def _combat_here(world: World, army: Army, war: War, enemy: str) -> None:
    here = [a for a in world.armies
            if a.country == enemy and a.region == army.region]
    ea = army.strength * army.org / 100
    ed = sum(a.strength * a.org / 100 for a in here) + 10

    army.org -= 1.0
    for a in here:
        a.org -= 1.0

    if ea > ed:
        winner = army.country
        loser = enemy
        margin = (ea - ed) / max(ea, 1)
        world.wars[war.id].battles_won[winner] = \
            world.wars[war.id].battles_won.get(winner, 0) + 1
        for a in here:
            a.strength *= (1 - 0.15 * margin)
            a.org -= 10 * margin
        army.strength *= (1 - 0.05 * margin)
        if army.org > 20 and world.regions[army.region].owner == enemy:
            reg = world.regions[army.region]
            reg.controlled = True
            reg.occupier = army.country
            world.wars[war.id].occupied[army.region] = army.country
            wc = world.country_obj(army.country)
            world.add_log(f"{wc.name if wc else army.country} occupies region {army.region}")
    else:
        winner = enemy
        loser = army.country
        margin = (ed - ea) / max(ed, 1)
        world.wars[war.id].battles_won[winner] = \
            world.wars[war.id].battles_won.get(winner, 0) + 1
        army.strength *= (1 - 0.2 * margin)
        army.org -= 15 * margin
        for a in here:
            a.strength *= (1 - 0.08 * margin)

    if army.org <= 0 or army.strength <= 5:
        if army in world.armies:
            world.armies.remove(army)
        wc = world.country_obj(loser)
        world.add_log(f"{wc.name if wc else loser} army destroyed")


def math_dist(x1, y1, x2, y2) -> float:
    import math
    return math.hypot(x1 - x2, y1 - y2)


def peace_options(world: World, war_id: str) -> List[dict]:
    war = world.wars[war_id]
    sc = world.selected_country
    if not sc or sc not in (war.attacker, war.defender):
        return []
    score = war.war_score
    enemy = war.defender if sc == war.attacker else war.attacker
    ec = world.country_obj(enemy)
    c = world.country_obj(sc)
    opts: List[dict] = []
    if score >= 5:
        opts.append({"kind": "white_peace", "label": "White peace", "score": 0})
    if score >= 20:
        for rid, occ in war.occupied.items():
            if occ == sc:
                reg = world.regions[rid]
                opts.append({"kind": "annex", "label": f"Annex region {rid}", "score": 10,
                             "region": rid, "target": reg.owner})
    if score >= 40 and ec:
        opts.append({"kind": "release_vassal", "label": f"Release {ec.name} as vassal", "score": 15,
                     "target": enemy})
    if score >= 50:
        opts.append({"kind": "vassalize", "label": f"Vassalize {ec.name if ec else enemy}", "score": 30,
                     "target": enemy})
    if score >= 70 and ec:
        opts.append({"kind": "force_religion", "label": f"Force {ec.religion}-> {c.religion if c else ''}", "score": 40,
                     "target": enemy})
    if score >= 90 and ec:
        opts.append({"kind": "force_ideology", "label": f"Force ideology ({c.ideology if c else ''})", "score": 50,
                     "target": enemy})
    if score >= 60 and ec:
        opts.append({"kind": "reparations", "label": f"Demand reparations from {ec.name if ec else enemy}", "score": 20,
                     "target": enemy})
    return opts


def apply_peace(world: World, war_id: str, terms: dict) -> None:
    war = world.wars[war_id]
    sc = world.selected_country
    enemy = war.defender if sc == war.attacker else war.attacker
    c = world.country_obj(sc)
    ec = world.country_obj(enemy)
    mult, cb_name = CB_TABLE.get(war.cb, CB_TABLE["conquest"])

    if terms["kind"] == "white_peace":
        world.add_log(f"Peace: white peace between {c.name if c else sc} and {ec.name if ec else enemy}")
    elif terms["kind"] == "annex" and terms.get("region") is not None:
        rid = terms["region"]
        from influence import set_region_owner
        set_region_owner(world, rid, sc)
        reg = world.regions[rid]
        reg.controlled = False
        reg.occupier = None
        war.occupied.pop(rid, None)
        world.add_log(f"Peace: {c.name if c else sc} annexes region {rid}")
    elif terms["kind"] == "vassalize":
        if ec:
            ec.vassal_of = sc
        if c:
            c.vassals.add(enemy)
        world.add_log(f"Peace: {ec.name if ec else enemy} becomes vassal of {c.name if c else sc}")
    elif terms["kind"] == "release_vassal":
        if ec and ec.vassal_of == sc:
            ec.vassal_of = None
            if c:
                c.vassals.discard(enemy)
            world.add_log(f"Peace: {ec.name if ec else enemy} released from vassalage")
    elif terms["kind"] == "force_religion":
        if ec:
            new_rel = world.countries[sc].religion if c else ""
            old_rel = ec.religion
            ec.religion = new_rel
            # seed the enemy's regions with the new religion
            for reg in world.regions.values():
                if reg.owner == enemy and old_rel in reg.religion:
                    reg.religion = {new_rel: 1.0}
            world.add_log(f"Peace: religion of {ec.name if ec else enemy} forced to {new_rel}")
    elif terms["kind"] == "force_ideology":
        if ec:
            old_ide = ec.ideology
            ec.ideology = world.countries[sc].ideology if c else ""
            world.add_log(f"Peace: ideology of {ec.name if ec else enemy} forced to {ec.ideology}")
    elif terms["kind"] == "reparations":
        if ec and c:
            amount = 40.0 * mult
            pay = min(ec.treasury, amount)
            ec.treasury -= pay
            c.treasury += pay
            world.add_log(f"Peace: {ec.name if ec else enemy} pays {pay:.0f} reparations to {c.name if c else sc}")

    war.active = False
    # clear guarantees that were consumed by this war
    if sc:
        c.guarantees.discard(enemy)
        ec.guaranteed_by.discard(sc) if ec else None
    for reg in world.regions.values():
        if reg.occupier:
            reg.controlled = False
            reg.occupier = None
    war.occupied.clear()
    world.add_log("Peace treaty signed")
