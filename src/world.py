"""Domain model: countries, houses, religions, cultures, ideologies, regions,
armies, fronts, wars. The World is the single source of truth for the sim."""
from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from core import DEFAULT_COUNTRY_COLORS, MAP_H, MAP_W, GameDate


# ---------------------------------------------------------------- factories
def new_tag(existing: Set[str], rng: random.Random) -> str:
    while True:
        tag = "".join(rng.choice(string.ascii_uppercase) for _ in range(3))
        if tag not in existing:
            return tag


def rand_color(rng: random.Random) -> Tuple[int, int, int]:
    return (
        rng.randint(50, 230),
        rng.randint(40, 220),
        rng.randint(40, 220),
    )


# ---------------------------------------------------------------- data
@dataclass
class Religion:
    id: str
    name: str
    color: Tuple[int, int, int]
    spread: float = 1.0
    hostility: Dict[str, float] = field(default_factory=dict)


@dataclass
class Culture:
    id: str
    name: str
    color: Tuple[int, int, int]
    spread: float = 1.0


@dataclass
class Ideology:
    id: str
    name: str
    color: Tuple[int, int, int]
    spread: float = 1.0


@dataclass
class House:
    id: str
    name: str
    color: Tuple[int, int, int]


@dataclass
class Country:
    tag: str
    name: str
    color: Tuple[int, int, int]
    religion: str = ""
    culture: str = ""
    ideology: str = ""
    house: str = ""
    capital: Optional[int] = None
    treasury: float = 100.0
    manpower: float = 100.0
    relations: Dict[str, float] = field(default_factory=dict)
    allies: Set[str] = field(default_factory=set)
    guarantees: Set[str] = field(default_factory=set)  # countries we defend if attacked
    guaranteed_by: Set[str] = field(default_factory=set)  # countries defending us
    royal_marriages: Set[str] = field(default_factory=set)  # house ties
    vassal_of: Optional[str] = None
    vassals: Set[str] = field(default_factory=set)
    ai_enabled: bool = True
    player: bool = False

    def relation(self, other: str) -> float:
        return self.relations.get(other, 0.0)


@dataclass
class Region:
    rid: int
    cells: List[Tuple[int, int]] = field(default_factory=list)
    center: Tuple[float, float] = (0.0, 0.0)
    owner: Optional[str] = None
    terrain: str = "plains"
    fort: int = 0
    religion: Dict[str, float] = field(default_factory=dict)
    culture: Dict[str, float] = field(default_factory=dict)
    ideology: Dict[str, float] = field(default_factory=dict)
    house: Dict[str, float] = field(default_factory=dict)
    controlled: bool = False
    occupier: Optional[str] = None

    def dominant(self, kind: str) -> Optional[str]:
        d = getattr(self, kind)
        if not d:
            return None
        return max(d, key=d.get)


@dataclass
class Army:
    id: int
    country: str
    region: int
    strength: float = 60.0
    org: float = 100.0
    morale: float = 50.0
    target: Optional[int] = None
    front: Optional[str] = None
    x: float = 0.0
    y: float = 0.0


@dataclass
class Front:
    id: str
    war: str
    a: str
    b: str
    regions: List[int] = field(default_factory=list)


@dataclass
class War:
    id: str
    attacker: str
    defender: str
    cb: str = "conquest"
    started: int = 0
    occupied: Dict[int, str] = field(default_factory=dict)
    battles_won: Dict[str, int] = field(default_factory=dict)
    war_score: float = 0.0
    active: bool = True
    front_ids: List[str] = field(default_factory=list)


@dataclass
class PeaceTerms:
    kind: str
    target: str = ""
    region: Optional[int] = None
    war_score_needed: float = 0.0


# ---------------------------------------------------------------- World
class World:
    def __init__(self, seed: int = 0, n_countries: int = 10, n_regions: int = 700):
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.date = GameDate()
        self.day_index = 0

        self.regions: Dict[int, Region] = {rid: Region(rid=rid) for rid in range(n_regions)}
        self.countries: Dict[str, Country] = {}
        self.houses: Dict[str, House] = {}
        self.religions: Dict[str, Religion] = {}
        self.cultures: Dict[str, Culture] = {}
        self.ideologies: Dict[str, Ideology] = {}

        self.region_grid: np.ndarray = np.empty((MAP_H, MAP_W), dtype=np.int32)
        self.region_grid.fill(-1)

        self.armies: List[Army] = []
        self.wars: Dict[str, War] = {}
        self.fronts: Dict[str, Front] = {}
        self._army_counter = 0
        self._region_adjacency: Dict[int, Set[int]] = {}

        self.selected_country: Optional[str] = None
        self.selected_region: Optional[int] = None
        self.border_editor: bool = False

        self.log: List[str] = []

        self._setup_factors()
        self._setup_countries(n_countries, n_regions)
        self._setup_armies()

    # ---------------------------------------------------------------- setup
    def _setup_factors(self) -> None:
        r = self.rng
        religions = [
            ("sun", "Solarism", (255, 180, 60)),
            ("moon", "Lunatism", (120, 140, 230)),
            ("star", "Star Faith", (200, 120, 240)),
            ("earth", "Earthen", (100, 180, 80)),
            ("void", "Void Cult", (140, 100, 160)),
        ]
        for rid, name, color in religions:
            self.religions[rid] = Religion(rid, name, color,
                                           spread=r.uniform(0.8, 1.2))

        cultures = [
            ("nor", "Northern", (110, 160, 220)),
            ("sou", "Southern", (230, 140, 70)),
            ("eas", "Eastern", (180, 110, 60)),
            ("wes", "Western", (140, 200, 110)),
            ("cen", "Central", (180, 150, 100)),
        ]
        for rid, name, color in cultures:
            self.cultures[rid] = Culture(rid, name, color, spread=r.uniform(0.8, 1.2))

        ideologies = [
            ("mon", "Monarchy", (160, 130, 90)),
            ("rep", "Republic", (80, 140, 190)),
            ("the", "Theocracy", (200, 100, 100)),
        ]
        for rid, name, color in ideologies:
            self.ideologies[rid] = Ideology(rid, name, color, spread=r.uniform(0.8, 1.2))

        houses = [
            ("h1", "House Draven", (170, 60, 60)),
            ("h2", "House Viridian", (70, 160, 90)),
            ("h3", "House Aurelian", (210, 170, 50)),
            ("h4", "House Obsidian", (110, 90, 130)),
        ]
        for hid, name, color in houses:
            self.houses[hid] = House(hid, name, color)

        rl_ids = list(self.religions)
        for a in rl_ids:
            for b in rl_ids:
                if a != b:
                    self.religions[a].hostility[b] = r.uniform(0.05, 0.3)

    def _setup_countries(self, n_countries: int, n_regions: int) -> None:
        tags: Set[str] = set()
        region_ids = list(range(n_regions))
        self.rng.shuffle(region_ids)

        for i in range(n_countries):
            tag = new_tag(tags, self.rng)
            tags.add(tag)
            color = DEFAULT_COUNTRY_COLORS[i % len(DEFAULT_COUNTRY_COLORS)]
            rel = self.rng.choice(list(self.religions))
            cul = self.rng.choice(list(self.cultures))
            ide = self.rng.choice(list(self.ideologies))
            hou = self.rng.choice(list(self.houses))
            c = Country(
                tag=tag,
                name=self._country_name(tag),
                color=color,
                religion=rel, culture=cul, ideology=ide, house=hou,
                treasury=self.rng.uniform(80, 160),
                manpower=self.rng.uniform(60, 120),
                ai_enabled=True,
                player=(i == 0),
            )
            self.countries[tag] = c

            start = i * (n_regions // n_countries)
            if i < n_countries - 1:
                owned = region_ids[start:start + (n_regions // n_countries)]
            else:
                owned = region_ids[start:]
            for rid in owned:
                reg = self.regions[rid]
                reg.owner = tag
                reg.religion = {rel: 1.0}
                reg.culture = {cul: 1.0}
                reg.ideology = {ide: 1.0}
                reg.house = {hou: 1.0}
                if c.capital is None:
                    c.capital = rid

        for a in self.countries.values():
            for b in self.countries.values():
                if a.tag != b.tag:
                    base = self.rng.uniform(-15, 25)
                    if a.religion == b.religion:
                        base += 10
                    if a.culture == b.culture:
                        base += 10
                    if a.ideology == b.ideology:
                        base += 5
                    a.relations[b.tag] = max(-100, min(100, base))

    def _country_name(self, tag: str) -> str:
        styles = [
            "the {} Kingdom", "{} Republic", "{} Dominion", "{} Empire",
            "{} Confederation", "{} Hegemony", "{} Principality",
        ]
        prefixes = [
            "Aldar", "Bryn", "Cel", "Durn", "Elth", "Fen", "Gar", "Holt",
            "Ivor", "Joren", "Kael", "Lorn", "Myr", "Nyx", "Orin", "Pax",
            "Quin", "Rhos", "Syl", "Thane", "Ulor", "Voss", "Wren", "Xan",
            "Yul", "Zan",
        ]
        style = self.rng.choice(styles)
        pre = self.rng.choice(prefixes)
        return style.format(pre)

    def _setup_armies(self) -> None:
        for tag, c in self.countries.items():
            if c.capital is None:
                continue
            self._army_counter += 1
            reg = self.regions[c.capital]
            self.armies.append(Army(
                id=self._army_counter,
                country=tag,
                region=c.capital,
                x=float(reg.center[0]),
                y=float(reg.center[1]),
                strength=self.rng.uniform(40, 80),
            ))

    # ---------------------------------------------------------------- helpers
    def country_obj(self, tag: Optional[str]) -> Optional[Country]:
        return self.countries.get(tag) if tag else None

    def region_obj(self, rid: int) -> Optional[Region]:
        return self.regions.get(rid)

    def add_log(self, text: str) -> None:
        self.log.append(text)
        if len(self.log) > 200:
            self.log.pop(0)

    def neighbors_of_region(self, rid: int) -> Set[int]:
        return self._region_adjacency.get(rid, set())

    def build_region_adjacency(self) -> None:
        """Static Voronoi topology: neighbouring region ids per region."""
        adj: Dict[int, Set[int]] = {rid: set() for rid in self.regions}
        h, wd = self.region_grid.shape
        for y in range(h):
            for x in range(wd):
                me = int(self.region_grid[y, x])
                for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < wd and 0 <= ny < h:
                        other = int(self.region_grid[ny, nx])
                        if other != -1 and other != me:
                            adj[me].add(other)
                            adj[other].add(me)
        self._region_adjacency = adj

    def adjacent_regions(self, rid: int) -> List[int]:
        return sorted(self.neighbors_of_region(rid))

    def border_region_pairs(self) -> List[Tuple[int, int]]:
        pairs: Set[Tuple[int, int]] = set()
        for rid, reg in self.regions.items():
            o1 = reg.owner
            if o1 is None:
                continue
            for nb in self.adjacent_regions(rid):
                o2 = self.regions[nb].owner
                if o2 is not None and o1 != o2:
                    pairs.add(tuple(sorted((rid, nb))))
        return sorted(pairs)
