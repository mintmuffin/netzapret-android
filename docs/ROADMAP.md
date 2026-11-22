# Release Roadmap

## v0.1 — Sandbox prototype (this release)
- Procedural Voronoi map, ~750 regions, 12 countries
- Countries: religion, culture, ideology, house (dynasty), treasury, manpower
- Gradual influence spread — fuzzy, moving religion/culture/ideology frontiers
- Dynamic borders computed from ownership; border editor (redraw any border anytime)
- Map modes: Political, Religion, Culture, Ideology, House, Terrain, Relations
- AI countries: relations drift, war declarations, border claims, army recruitment
- Frontline armies with combat and occupation
- Wars with war score; peace treaties: white peace, annex, vassalize, force religion
- Time-lapse: pause, 1x, 5x, 20x, 100x
- Event log, country/region inspector
- Portable zip build (Windows via Wine + Linux) via GitHub Actions → GitHub Release

## v0.2 — Diplomacy & depth
- Guarantees, royal marriages, personal unions (houses)
- Casus belli system (reconquest, holy war, ideology war)
- Peace terms: release nation, change government/ideology, reparations
- AI alliance building and coalition wars

## v0.3 — Map & world
- Terrain effects on combat and movement
- Rivers, coasts, sea zones and naval movement
- Region development, forts, supply
- Custom map editor / save & load games

## v0.4 — Player-facing
- Country selection at start, missions/objectives
- Monarch/house events and succession crises
- Religion reformation, culture conversion decisions
- Notifications and ledger

## Tech & build
- Engine: Python 3.11 + Pygame + numpy
- Portable: PyInstaller one-folder, zipped per platform
- CI: GitHub Actions builds + GitHub Release assets
- Repo limit: keep assets under ~128 MB; no committed binaries
