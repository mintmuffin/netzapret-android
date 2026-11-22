# NetZapret: Timelapse Grand Strategy Sandbox — Game Design

## Vision
A **sandbox / spectator grand strategy** in the spirit of *Fantasy Map Simulator*, *Hearts of Iron IV*, *Europa Universalis IV* and *Edge of Power*, but built around **time-lapse** and **fully redrawable borders**. There are no fixed provinces — the map is generated, borders are computed from ownership claims, and any country (including the player via the border editor) can redraw them at any time. Religions, cultures and ideologies spread **gradually across continuous influence fields**, not province-by-province. AI countries run the world while the player watches, intervenes, or plays god with the border tool.

## Core pillars
1. **No fixed borders.** Regions are generated (Voronoi). Ownership is a claim per region; borders are the lines between differing owners. Redraw any border, any time.
2. **Gradual cultural/religious/ideological influence.** Each map point holds continuous 0..1 mixes; influence projects from owned regions and decays with distance. Borders of faith/culture/ideology are fuzzy, shifting frontiers — not hard lines.
3. **Houses (dynasties).** Multiple houses exist inside one country; a country's ruling house determines bonuses and succession drama. Regions support houses too.
4. **Frontline wars.** Wars push a front line, not a "paint the map" blob. Occupied territory behind the front changes hands at peace.
5. **Peace treaties.** Demand regions, vassalization, white peace, force government/religion, independence.
6. **AI sandbox.** Every country has an AI; the game is fun to watch at 100x speed. Player is optional — spectator mode is a first-class feature.

## Entities
- **Country:** tag, name, color, capital, religion, culture, ideology, ruling house, treasury, manpower, relations with every other country, alliances.
- **House (dynasty):** name, color, member countries, traits.
- **Religion / Culture / Ideology:** name, color, spread strength, hostility toward others.
- **Region:** polygon of map cells, owner, terrain, development, mixes for religion/culture/ideology/house support, fort level.
- **Army:** country, strength, organization, location (region/front), morale.
- **Frontline:** segment between two armies at war; combat ticks here; the stronger side advances into enemy regions.
- **War:** attacker, defender, casus belli, war score (from occupied regions + battle results), status.
- **Peace treaty:** terms generated from war score — transfer regions, release vassals, white peace, change religion/government.

## Time
- Calendar: year/month/day.
- Speeds: Pause, 1x, 5x, 20x, 100x. Every tick runs influence spread; AI and army combat run every N days.

## Map modes
Political (owner), Religion, Culture, Ideology, House, Terrain, Relations, Border Editor.

## Build
- Engine: Python + Pygame + numpy.
- Portable zip: PyInstaller one-folder build, zipped per platform.
- CI: GitHub Actions builds Windows (via Wine) + Linux portable zips and publishes a GitHub Release.
