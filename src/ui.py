"""Pygame rendering and UI: map view, panels, buttons, map modes."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame

from core import (COLOR_BORDER, COLOR_UI_BG, COLOR_UI_LINE, COLOR_UI_PANEL,
                  COLOR_SELECT, COLOR_TEXT, COLOR_TEXT_DIM, MAP_H, MAP_W,
                  SCREEN_H, SCREEN_W)
from influence import dominant_factor_color
from world import World


class Button:
    def __init__(self, rect: pygame.Rect, text: str):
        self.rect = rect
        self.text = text
        self.hover = False
        self.active = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        color = (90, 100, 120) if self.hover else (60, 70, 90)
        if self.active:
            color = (120, 160, 60)
        pygame.draw.rect(surf, color, self.rect, border_radius=4)
        pygame.draw.rect(surf, COLOR_UI_LINE, self.rect, width=2, border_radius=4)
        txt = font.render(self.text, True, COLOR_TEXT)
        surf.blit(txt, txt.get_rect(center=self.rect.center))


class UI:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.Font(None, 20)
        self.font_big = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 16)
        self.panel_w = 340
        self.map_rect = pygame.Rect(0, 0, SCREEN_W - self.panel_w, SCREEN_H)
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 6.0
        self.buttons: List = []

    # ---------------------------------------------------------------- map
    def draw_map(self, world: World, mode: str, selected_country: Optional[str],
                 selected_region: Optional[int],
                 occupied: Dict[int, str]) -> None:
        map_surf = pygame.Surface((MAP_W, MAP_H))
        arr = pygame.surfarray.pixels3d(map_surf)
        for rid, reg in world.regions.items():
            col = dominant_factor_color(world, reg, mode)
            for (cx, cy) in reg.cells:
                arr[cx, cy] = col
        del arr
        scaled = pygame.transform.scale(map_surf, (MAP_W * int(self.zoom),
                                                   MAP_H * int(self.zoom)))
        self.screen.blit(scaled, (int(-self.camera_x * self.zoom),
                                  int(-self.camera_y * self.zoom)))

        from influence import compute_border_lines
        lines = compute_border_lines(world)
        for (x1, y1, x2, y2) in lines:
            p1 = self._to_screen(x1, y1)
            p2 = self._to_screen(x2, y2)
            pygame.draw.line(self.screen, COLOR_BORDER, p1, p2, 2)

        for rid, tag in occupied.items():
            reg = world.regions[rid]
            p = self._to_screen(reg.center[0], reg.center[1])
            pygame.draw.circle(self.screen, (200, 60, 60), p, 5, 2)
            pygame.draw.circle(self.screen, (200, 60, 60), p, 3)

        for army in world.armies:
            c = world.countries.get(army.country)
            col = c.color if c else (180, 180, 180)
            p = self._to_screen(army.x, army.y)
            r = 6
            pygame.draw.circle(self.screen, col, p, r)
            pygame.draw.circle(self.screen, (0, 0, 0), p, r, 2)
            pygame.draw.rect(self.screen, (120, 40, 40),
                             (p[0] - r, p[1] + r + 2, r * 2, 3))
            pygame.draw.rect(self.screen, (80, 200, 80),
                             (p[0] - r, p[1] + r + 2,
                              int(r * 2 * army.org / 100), 3))

        if selected_region is not None:
            reg = world.regions[selected_region]
            for (cx, cy) in reg.cells:
                p = self._to_screen(cx, cy)
                pygame.draw.rect(self.screen, COLOR_SELECT,
                                 (p[0], p[1], max(1, int(self.zoom)),
                                  max(1, int(self.zoom))), 1)

    def _to_screen(self, x: float, y: float) -> Tuple[int, int]:
        return (int((x - self.camera_x) * self.zoom),
                int((y - self.camera_y) * self.zoom))

    def screen_to_cell(self, sx: int, sy: int) -> Tuple[float, float]:
        return (sx / self.zoom + self.camera_x,
                sy / self.zoom + self.camera_y)

    # ---------------------------------------------------------------- UI panel
    def draw_panel(self, world: World, speed: int, paused: bool,
                   mode: str, war_peace_opts: List[dict]) -> List:
        self.buttons = []
        panel = pygame.Rect(SCREEN_W - self.panel_w, 0, self.panel_w, SCREEN_H)
        pygame.draw.rect(self.screen, COLOR_UI_PANEL, panel)
        pygame.draw.line(self.screen, COLOR_UI_LINE,
                         (panel.left, 0), (panel.left, SCREEN_H), 2)

        x = panel.left + 15
        y = 15
        self.screen.blit(self.font_big.render("NETZAPRET", True, COLOR_TEXT), (x, y))
        y += 32
        self.screen.blit(self.font.render(f"Date: {world.date}", True, COLOR_TEXT_DIM), (x, y))
        y += 20
        self.screen.blit(self.font.render(f"Day: {world.day_index}", True, COLOR_TEXT_DIM), (x, y))
        y += 30

        self.screen.blit(self.font.render("Speed", True, COLOR_TEXT), (x, y))
        y += 20
        speeds = [("PAUSE", 0), ("1x", 1), ("5x", 5), ("20x", 20), ("100x", 100)]
        for label, val in speeds:
            b = Button(pygame.Rect(x, y, 52, 24), label)
            b.active = (val == speed)
            b.draw(self.screen, self.font)
            self.buttons.append(("speed", val, b.rect))
            y += 26
        y += 10

        self.screen.blit(self.font.render("Map mode", True, COLOR_TEXT), (x, y))
        y += 20
        modes = [("Political", "political"), ("Religion", "religion"),
                 ("Culture", "culture"), ("Ideology", "ideology"),
                 ("House", "house"), ("Terrain", "terrain"),
                 ("Relations", "relations")]
        for label, m in modes:
            b = Button(pygame.Rect(x, y, 100, 24), label)
            b.active = (m == mode)
            b.draw(self.screen, self.font)
            self.buttons.append(("mode", m, b.rect))
            y += 26
        y += 10

        b = Button(pygame.Rect(x, y, 140, 26),
                   f"Border editor: {'ON' if world.border_editor else 'OFF'}")
        b.active = world.border_editor
        b.draw(self.screen, self.font)
        self.buttons.append(("editor", None, b.rect))
        y += 32

        c = world.country_obj(world.selected_country)
        self.screen.blit(self.font.render("Selected country", True, COLOR_TEXT), (x, y))
        y += 20
        if c:
            self._line(x, y, f"{c.name} [{c.tag}]", COLOR_TEXT); y += 18
            self._line(x, y, f"Religion: {c.religion}", COLOR_TEXT); y += 18
            self._line(x, y, f"Culture: {c.culture}", COLOR_TEXT); y += 18
            self._line(x, y, f"Ideology: {c.ideology}", COLOR_TEXT); y += 18
            self._line(x, y, f"House: {c.house}", COLOR_TEXT); y += 18
            self._line(x, y, f"Treasury: {c.treasury:.0f}", COLOR_TEXT); y += 18
            self._line(x, y, f"Manpower: {c.manpower:.0f}", COLOR_TEXT); y += 18
            self.screen.blit(self.font.render("Relations", True, COLOR_TEXT), (x, y))
            y += 18
            for tag, rel in sorted(c.relations.items(), key=lambda kv: -kv[1]):
                oc = world.countries.get(tag)
                name = oc.name if oc else tag
                col = (120, 220, 120) if rel > 20 else ((220, 120, 120) if rel < -20 else COLOR_TEXT_DIM)
                self._line(x, y, f"{name}: {rel:.0f}", col); y += 16
        else:
            self._line(x, y, "(none)", COLOR_TEXT_DIM); y += 18
        y += 10

        r = world.regions[world.selected_region] if world.selected_region is not None else None
        self.screen.blit(self.font.render("Selected region", True, COLOR_TEXT), (x, y))
        y += 20
        if r:
            self._line(x, y, f"id {r.rid}  {r.terrain}", COLOR_TEXT); y += 16
            self._line(x, y, f"owner: {r.owner or 'none'}", COLOR_TEXT); y += 16
            self._line(x, y, f"religion: {r.dominant('religion') or '-'}", COLOR_TEXT); y += 16
            self._line(x, y, f"culture: {r.dominant('culture') or '-'}", COLOR_TEXT); y += 16
        else:
            self._line(x, y, "(none)", COLOR_TEXT_DIM); y += 18
        y += 14

        if war_peace_opts:
            self.screen.blit(self.font.render("Peace terms", True, COLOR_TEXT), (x, y))
            y += 20
            for opt in war_peace_opts:
                b = Button(pygame.Rect(x, y, self.panel_w - 30, 22), opt["label"])
                b.draw(self.screen, self.font)
                self.buttons.append(("peace", opt, b.rect))
                y += 24
            y += 10

        self.screen.blit(self.font.render("Event log", True, COLOR_TEXT), (x, y))
        y += 20
        log_h = SCREEN_H - y - 10
        log_rect = pygame.Rect(x, y, self.panel_w - 30, log_h)
        pygame.draw.rect(self.screen, COLOR_UI_BG, log_rect, border_radius=3)
        iy = y + log_h - 18
        for line in reversed(world.log[-12:]):
            self.screen.blit(self.font_small.render(line, True, COLOR_TEXT_DIM),
                             (x + 4, iy))
            iy -= 17
            if iy < y + 4:
                break

        return self.buttons

    def _line(self, x, y, text, color):
        self.screen.blit(self.font.render(text, True, color), (x, y))
