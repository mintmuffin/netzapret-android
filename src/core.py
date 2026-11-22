"""Core constants, time, math helpers and shared config for NetZapret."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple

# ------------------------------------------------------------------ display
SCREEN_W = 1280
SCREEN_H = 800
MAP_W = 140          # logical map width in cells
MAP_H = 88           # logical map height in cells
CELL = 6             # render pixels per cell (scaled at runtime with zoom)
FPS = 60

# ------------------------------------------------------------------ time
DAYS_PER_MONTH = 30
MONTHS_PER_YEAR = 12
START_YEAR = 800


@dataclass
class GameDate:
    year: int = START_YEAR
    month: int = 1
    day: int = 1

    def advance(self, days: int) -> None:
        self.day += days
        while self.day > DAYS_PER_MONTH:
            self.day -= DAYS_PER_MONTH
            self.month += 1
            while self.month > MONTHS_PER_YEAR:
                self.month -= MONTHS_PER_YEAR
                self.year += 1

    def __str__(self) -> str:
        return f"{self.day:02d}.{self.month:02d}.{self.year}"


# ------------------------------------------------------------------ colors
COLOR_UI_BG = (22, 26, 34)
COLOR_UI_PANEL = (34, 40, 52)
COLOR_UI_LINE = (70, 80, 96)
COLOR_TEXT = (235, 240, 245)
COLOR_TEXT_DIM = (160, 170, 185)
COLOR_BORDER = (40, 45, 58)
COLOR_SELECT = (255, 215, 0)
COLOR_OCCUPIED = (200, 60, 60)

DEFAULT_COUNTRY_COLORS = [
    (220, 60, 60), (60, 120, 220), (60, 180, 90), (210, 160, 60),
    (190, 80, 210), (220, 200, 70), (80, 200, 200), (160, 100, 50),
    (140, 140, 160), (230, 100, 130), (90, 160, 230), (150, 210, 90),
]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def blend_color(c1, c2, t: float) -> Tuple[int, int, int]:
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )
