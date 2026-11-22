"""Main game loop: simulation, input, and the glue between world + UI."""
from __future__ import annotations

import math
import random

import pygame

from core import MAP_H, MAP_W, SCREEN_H, SCREEN_W
from diplomacy import tick_ai
from influence import set_region_owner, spread_influence
from mapgen import generate_map
from ui import UI
from war import apply_peace, peace_options, start_war, tick_armies
from world import World


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("NetZapret — Timelapse Grand Strategy Sandbox")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.ui = UI(self.screen)

        self.world = World(seed=4242, n_countries=12, n_regions=750)
        generate_map(self.world, 750, 4242)
        self.world.build_region_adjacency()

        self.speed = 1
        self.paused = False
        self.mode = "political"
        self.dragging = False
        self.last_mouse = (0, 0)
        self.hover_region = None
        self.accum = 0.0
        self.running = True

    # ---------------------------------------------------------------- events
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    self.speed = 0 if self.paused else 1
                elif event.key == pygame.K_b:
                    self.world.border_editor = not self.world.border_editor
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._on_left_click(event.pos)
                elif event.button == 3:
                    self._on_right_click(event.pos)
                elif event.button == 4:
                    self.zoom_at(event.pos, 1.2)
                elif event.button == 5:
                    self.zoom_at(event.pos, 1 / 1.2)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    mx, my = event.pos
                    lx, ly = self.last_mouse
                    self.ui.camera_x -= (mx - lx) / self.ui.zoom
                    self.ui.camera_y -= (my - ly) / self.ui.zoom
                    self._clamp_camera()
                self.last_mouse = event.pos
                self._update_hover(event.pos)

        mx, my = pygame.mouse.get_pos()
        for kind, value, rect in self.ui.buttons:
            if rect.collidepoint(mx, my) and pygame.mouse.get_pressed()[0]:
                self._on_button(kind, value)
                pygame.time.wait(120)

    def _on_button(self, kind, value):
        if kind == "speed":
            self.speed = value
            self.paused = (value == 0)
        elif kind == "mode":
            self.mode = value
        elif kind == "editor":
            self.world.border_editor = not self.world.border_editor
        elif kind == "peace":
            war = self._active_player_war()
            if war:
                apply_peace(self.world, war.id, value)

    def _active_player_war(self):
        tag = self.world.selected_country
        for w in self.world.wars.values():
            if w.active and tag in (w.attacker, w.defender):
                return w
        return None

    def _on_left_click(self, pos):
        if pos[0] > SCREEN_W - self.ui.panel_w:
            return
        wx, wy = self.ui.screen_to_cell(*pos)
        rid = int(self.world.region_grid[int(_clamp(wy, 0, MAP_H - 1)),
                                         int(_clamp(wx, 0, MAP_W - 1))])
        if rid < 0:
            return
        if self.world.border_editor:
            sc = self.world.selected_country
            if sc:
                set_region_owner(self.world, rid, sc)
            self.world.selected_region = rid
        else:
            reg = self.world.regions[rid]
            self.world.selected_region = rid
            if reg.owner:
                self.world.selected_country = reg.owner

    def _on_right_click(self, pos):
        if pos[0] > SCREEN_W - self.ui.panel_w:
            return
        wx, wy = self.ui.screen_to_cell(*pos)
        rid = int(self.world.region_grid[int(_clamp(wy, 0, MAP_H - 1)),
                                         int(_clamp(wx, 0, MAP_W - 1))])
        if rid < 0:
            return
        tag = self.world.selected_country
        if not tag:
            return
        my_armies = [a for a in self.world.armies if a.country == tag]
        if not my_armies:
            return
        reg = self.world.regions[rid]
        best = min(my_armies, key=lambda a: math.hypot(a.x - reg.center[0],
                                                       a.y - reg.center[1]))
        best.region = reg.rid
        best.target = reg.rid
        self.world.add_log(f"{tag}: army ordered to region {rid}")

    def _update_hover(self, pos):
        if pos[0] > SCREEN_W - self.ui.panel_w:
            self.hover_region = None
            return
        wx, wy = self.ui.screen_to_cell(*pos)
        self.hover_region = int(self.world.region_grid[int(_clamp(wy, 0, MAP_H - 1)),
                                                       int(_clamp(wx, 0, MAP_W - 1))])

    def zoom_at(self, pos, factor):
        wx, wy = self.ui.screen_to_cell(*pos)
        self.ui.zoom = max(2.0, min(14.0, self.ui.zoom * factor))
        nx, ny = self.ui.screen_to_cell(*pos)
        self.ui.camera_x += wx - nx
        self.ui.camera_y += wy - ny
        self._clamp_camera()

    def _clamp_camera(self):
        self.ui.camera_x = max(-40, min(MAP_W + 40, self.ui.camera_x))
        self.ui.camera_y = max(-40, min(MAP_H + 40, self.ui.camera_y))

    # ---------------------------------------------------------------- sim step
    def simulate(self, dt_days: float):
        if dt_days <= 0:
            return
        days = int(dt_days)
        frac = dt_days - days
        self.accum += frac
        while self.accum >= 1.0:
            days += 1
            self.accum -= 1.0

        for _ in range(days):
            self.world.day_index += 1
            self.world.date.advance(1)
            spread_influence(self.world)
            if self.world.day_index % 30 == 0:
                tick_ai(self.world)
        tick_armies(self.world)

        for w in list(self.world.wars.values()):
            if w.active and w.war_score > 90 and not self._player_involved(w):
                if random.random() < 0.02:
                    war_end_ai(self.world, w)

    def _player_involved(self, war) -> bool:
        tag = self.world.selected_country
        return tag in (war.attacker, war.defender)

    # ---------------------------------------------------------------- render
    def render(self):
        self.screen.fill((10, 12, 16))
        occupied = {}
        for w in self.world.wars.values():
            occupied.update(w.occupied)
        self.ui.draw_map(self.world, self.mode,
                         self.world.selected_country,
                         self.world.selected_region, occupied)
        war = self._active_player_war()
        self.ui.draw_panel(self.world, self.speed, self.paused, self.mode,
                           peace_options(self.world, war.id) if war else [])
        hint = ("LMB: select/paint border  |  RMB: move army  |  Wheel: zoom  |  "
                "Drag: pan  |  B: border editor  |  Space: pause")
        self.screen.blit(self.ui.font_small.render(hint, True, (120, 130, 150)),
                         (12, SCREEN_H - 22))
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            if not self.paused:
                self.simulate(self.speed * dt)
            self.render()
        pygame.quit()


def war_end_ai(world: World, war) -> None:
    war.active = False
    for reg in world.regions.values():
        if reg.occupier:
            reg.controlled = False
            reg.occupier = None
    war.occupied.clear()
    world.add_log(f"War {war.id} ended (AI peace)")


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    Game().run()


if __name__ == "__main__":
    main()
