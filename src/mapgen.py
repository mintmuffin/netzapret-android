"""Procedural map generation: Voronoi regions over a cell grid."""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from core import MAP_H, MAP_W
from world import Region, World


def generate_map(world: World, n_regions: int, seed: int) -> None:
    """Split the map into Voronoi regions and attach Region objects."""
    rng = np.random.default_rng(seed)

    xs = rng.uniform(0, MAP_W, size=n_regions)
    ys = rng.uniform(0, MAP_H, size=n_regions)
    seeds = np.column_stack([xs, ys])

    yy, xx = np.mgrid[0:MAP_H, 0:MAP_W]
    grid = np.stack([yy.astype(np.float32), xx.astype(np.float32)], axis=-1)

    d2 = ((grid[None, :, :, :] - seeds[:, None, None, :]) ** 2).sum(axis=-1)
    region_grid = d2.argmin(axis=0).astype(np.int32)

    region_grid = _smooth(region_grid, passes=2)

    world.region_grid = region_grid

    terrains = ["plains", "plains", "plains", "hills", "forest", "mountains", "desert"]
    for rid in range(n_regions):
        cells = list(zip(*np.where(region_grid == rid)))
        cells = [(int(x), int(y)) for (y, x) in cells]
        if not cells:
            continue
        cy = sum(c[0] for c in cells) / len(cells)
        cx = sum(c[1] for c in cells) / len(cells)
        reg = world.regions[rid]
        reg.cells = cells
        reg.center = (cx, cy)
        reg.terrain = world.rng.choice(terrains)


def _smooth(grid: np.ndarray, passes: int = 2) -> np.ndarray:
    h, w = grid.shape
    out = grid.copy()
    kernel = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for _ in range(passes):
        nxt = out.copy()
        for y in range(h):
            for x in range(w):
                me = out[y, x]
                counts: dict = {}
                for dy, dx in kernel:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        v = int(out[ny, nx])
                        counts[v] = counts.get(v, 0) + 1
                counts[int(me)] = counts.get(int(me), 0) + 3
                nxt[y, x] = max(counts, key=counts.get)
        out = nxt
    return out
