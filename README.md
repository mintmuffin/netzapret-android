# NetZapret — Timelapse Grand Strategy Sandbox

A *Fantasy Map Simulator* / *Hearts of Iron IV* / *Europa Universalis IV* inspired **sandbox grand strategy** with fully redrawable borders, gradual religion/culture/ideology influence, houses (dynasties), frontline wars, peace treaties, diplomacy, and AI countries. Built to be watched in time-lapse.

## Features (MVP)
- Procedurally generated map with Voronoi regions — no fixed provinces.
- Dynamic borders computed from regional ownership; redraw any border at any time (border editor).
- Countries with religion, culture, ideology and ruling house (dynasty).
- Continuous influence fields: religions/cultures/ideologies spread gradually across the map.
- Frontline wars with occupation and peace treaties (annex land, vassalize, white peace, force religion/government).
- Diplomacy: relations, alliances, guarantees.
- AI countries that expand, ally, and war autonomously.
- Time-lapse: pause, 1x, 5x, 20x, 100x.
- Map modes: Political, Religion, Culture, Ideology, House, Terrain, Relations.
- Portable zip build via GitHub Actions (PyInstaller).

## Tech
Python 3.11 + Pygame + numpy. One-folder PyInstaller portable builds.

## Run from source
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## Build portable zip (GitHub Actions)
Push to the repo; `.github/workflows/build.yml` builds Windows (via Wine) and Linux portable zips and attaches them to a GitHub Release tagged `v<version>`.

## Roadmap
See `docs/GAME_DESIGN.md` for the full design and `docs/ROADMAP.md` for the release plan.
