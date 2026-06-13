## pygame rendering layer — 3-row layout.
## Row 1: World | Location | Focus (3 panels)
## Row 2: Command output log (scrollable terminal-like)
## Row 3: Input bar
from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world_state import WorldState

# ── Window ────────────────────────────────────────────────────────

W = 1200; H = 750; FPS = 30

# Row heights
HEADER_H = 28
ROW1_H  = 340
ROW2_H  = 240
INPUT_H = 36
GAP = 6

# Panel widths in row 1
LEFT_W = 260
RIGHT_W = 220
MID_W = W - LEFT_W - RIGHT_W - GAP * 4 - 16

# Colours
C_BG   = (8, 8, 10)
C_PANEL = (16, 16, 22)
C_BORDER = (44, 44, 55)
C_WHITE = (210, 210, 210)
C_DIM   = (130, 130, 140)
C_GREEN = (0, 230, 90)
C_RED   = (230, 60, 60)
C_YELLOW = (230, 190, 40)
C_CYAN  = (40, 210, 210)
C_PURPLE = (170, 130, 230)
C_LOG_BG = (12, 12, 18)
C_INPUT_BG = (10, 10, 15)

EVENT_COLORS = {"daily": C_DIM, "development": C_WHITE,
                "conflict": C_RED, "turning": C_YELLOW}


class UI:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("神域微言")
        self.clock = pygame.time.Clock()
        pygame.key.start_text_input()
        self._font_path = self._find_font()
        self.f = pygame.font.Font(self._font_path, 13)
        self.fb = pygame.font.Font(self._font_path, 13); self.fb.bold = True
        self.fh = pygame.font.Font(self._font_path, 15); self.fh.bold = True
        self.fs = pygame.font.Font(self._font_path, 11)

    def _find_font(self) -> str:
        import os
        for p in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simsun.ttc",
                   "C:/Windows/Fonts/consola.ttf"]:
            if os.path.exists(p): return p
        return pygame.font.get_default_font()

    def render(self, world: WorldState, current_loc: str,
               current_sub: str, focused: set[str],
               input_text: str, log_lines: list[tuple[str, int]],
               ai_enabled: bool, paused: bool) -> None:
        self.screen.fill(C_BG)
        y = 6

        # ── Header ──
        time_str = world.time_string()
        war_str = ""
        if world.war_active:
            p = {"preparation": "备战", "skirmish": "冲突", "battle": "会战"}
            war_str = f"  ⚔ {p.get(world.war_phase, '')}"
        self._text(self.fh, f"神域微言 · {time_str}{war_str}", 12, y + 2, C_WHITE)
        y += HEADER_H + GAP

        # ══════════════ Row 1: 3 panels ══════════════
        row1_y = y
        lx = 8
        self._panel(lx, row1_y, LEFT_W, ROW1_H, "世界状态")
        self._draw_world(world, lx, row1_y, LEFT_W, ROW1_H)

        mx = lx + LEFT_W + GAP
        self._panel(mx, row1_y, MID_W, ROW1_H, "观察地点")
        self._draw_location(world, current_loc, current_sub, mx, row1_y, MID_W, ROW1_H)

        rx = mx + MID_W + GAP
        self._panel(rx, row1_y, RIGHT_W, ROW1_H, "聚焦角色")
        self._draw_focus(world, focused, rx, row1_y, RIGHT_W, ROW1_H)

        y = row1_y + ROW1_H + GAP

        # ══════════════ Row 2: Command log ══════════════
        self._draw_log(lx, y, W - 16, ROW2_H, log_lines)
        y += ROW2_H + GAP

        # ══════════════ Row 3: Input bar ══════════════
        pygame.draw.rect(self.screen, C_INPUT_BG, (lx, y, W - 16, INPUT_H))
        pygame.draw.rect(self.screen, C_BORDER, (lx, y, W - 16, INPUT_H), 1)
        mode = "[AI]" if ai_enabled else "[T]"
        pause_mark = " ⏸" if paused else ""
        cursor = "_" if pygame.time.get_ticks() % 800 < 400 else " "
        self._text(self.f, f"{mode}> {input_text}{cursor}",
                   lx + 8, y + INPUT_H // 2 - 7, C_GREEN)

        pygame.display.flip()

    # ── Row 1: World panel ───────────────────────────────────────

    def _draw_world(self, world: WorldState, x: int, y: int,
                    w: int, h: int) -> None:
        yy = y + 28
        human = len([c for c in world.characters.values()
                     if c.race == "human" and c.status == "alive"])
        demon = len([c for c in world.characters.values()
                     if c.race == "demon" and c.status == "alive"])
        yy = self._line(x + 8, yy, f"人类: {human}  魔族: {demon}", C_DIM, w - 16)
        yy += 4
        from game.world_state import LOCATIONS
        for lid in ["academy", "front", "throne", "demon", "village"]:
            cnt = len([c for c in world.characters.values()
                       if c.location == lid and c.status == "alive"])
            color = C_RED if world.war_active and lid == "front" else C_DIM
            yy = self._line(x + 8, yy, f"{LOCATIONS[lid]['name']}: {cnt}人", color, w - 16)
        if world.narrative_threads:
            yy += 6
            yy = self._line(x + 8, yy, "叙事线:", C_DIM, w - 16)
            for tid, mom in sorted(world.narrative_threads.items(),
                                    key=lambda kv: -kv[1])[:4]:
                bar = "#" * int(mom) + "-" * max(0, 5 - int(mom))
                yy = self._line(x + 8, yy, f"  {tid}: {bar}", C_PURPLE, w - 16)

    # ── Row 1: Location panel ────────────────────────────────────

    def _draw_location(self, world: WorldState, loc_id: str,
                       sub: str, x: int, y: int, w: int, h: int) -> None:
        yy = y + 28
        if not loc_id:
            self._line(x + 8, yy, "输入 goto [地点] 开始观察。", C_DIM, w - 16)
            return
        from game.world_state import LOCATIONS
        loc = LOCATIONS[loc_id]
        yy = self._line(x + 8, yy, loc["name"], C_WHITE, w - 16, bold=True)
        if sub:
            # Show sub in en (zh) format
            sub_display = _sub_display_name(sub, loc)
            yy = self._line(x + 8, yy, f"  ▸ {sub_display}", C_CYAN, w - 16)
        chars = world.get_characters_at(loc_id)
        if chars:
            names = "、".join(c.name for c in chars)
            yy = self._line(x + 8, yy, f"在场: {names}", C_DIM, w - 16)
        yy += 4
        recent = [e for e in world.all_events[-80:]
                  if e.get("location") == loc_id]
        if sub:
            recent = [e for e in recent if e.get("sub_location") == sub]
        for ev in recent[-12:]:
            color = EVENT_COLORS.get(ev.get("priority", "daily"), C_DIM)
            yy = self._line(x + 8, yy, ev["text"], color, w - 16)
            if yy > y + h - 16:
                break

    # ── Row 1: Focus panel ───────────────────────────────────────

    def _draw_focus(self, world: WorldState, focused: set[str],
                    x: int, y: int, w: int, h: int) -> None:
        yy = y + 28
        if not focused:
            self._line(x + 8, yy, "输入 focus [名字]", C_DIM, w - 16)
            self._line(x + 8, yy + 18, "关注角色", C_DIM, w - 16)
            return
        for name in list(focused)[:3]:
            matches = [c for c in world.characters.values() if c.name == name]
            if not matches: continue
            ch = matches[0]
            yy = self._line(x + 8, yy, f"● {ch.name}", C_CYAN, w - 16, bold=True)
            yy = self._line(x + 8, yy, f"  {ch.role or ch.race}", C_DIM, w - 16)
            for attr, val in [("战力", ch.combat), ("魔力", ch.magic),
                               ("意志", ch.will), ("社交", ch.social)]:
                yy = self._line(x + 8, yy,
                    f"  {attr}: {'#' * (val // 10)}{'-' * (10 - val // 10)} {val}",
                    C_WHITE, w - 16)
            from game.world_state import get_location_name
            yy = self._line(x + 8, yy, f"  位置: {get_location_name(ch.location)}",
                           C_DIM, w - 16)
            yy += 4

    # ── Row 2: Command log ───────────────────────────────────────

    def _draw_log(self, x: int, y: int, w: int, h: int,
                  lines: list[tuple[str, int]]) -> None:
        pygame.draw.rect(self.screen, C_LOG_BG, (x, y, w, h))
        pygame.draw.rect(self.screen, C_BORDER, (x, y, w, h), 1)
        self._text(self.fs, "命令记录", x + 6, y + 3, C_DIM)

        # Show last N lines from bottom
        yy = y + h - 18
        for text, color_int in reversed(lines):
            r = (color_int >> 16) & 0xFF
            g = (color_int >> 8) & 0xFF
            b = color_int & 0xFF
            txt = self._fit(text, w - 16, self.fs)
            yy -= 16
            self._text(self.fs, txt, x + 8, yy, (r, g, b))

    # ── Helpers ───────────────────────────────────────────────────

    def _panel(self, x: int, y: int, w: int, h: int, title: str) -> None:
        pygame.draw.rect(self.screen, C_PANEL, (x, y, w, h))
        pygame.draw.rect(self.screen, C_BORDER, (x, y, w, h), 1)
        self._text(self.fs, title, x + 6, y + 4, C_DIM)

    def _text(self, font, txt: str, x: int, y: int, r: int, g: int = 0, b: int = 0) -> None:
        if isinstance(r, tuple):
            color = r
        else:
            color = (r, g, b)
        surf = font.render(txt, True, color)
        self.screen.blit(surf, (x, y))

    def _line(self, x: int, y: int, txt: str, color: tuple,
              max_w: int, bold: bool = False) -> int:
        font = self.fb if bold else self.f
        txt = self._fit(txt, max_w, font)
        h = font.get_height()
        self._text(font, txt, x, y, color)
        return y + h + 1

    def _fit(self, txt: str, max_w: int, font: pygame.font.Font) -> str:
        if font.size(txt)[0] <= max_w:
            return txt
        while len(txt) > 10 and font.size(txt + "…")[0] > max_w:
            txt = txt[:-1]
        return txt + "…"


# ── Module-level helpers ──────────────────────────────────────────

def _sub_display_name(sub_zh: str, loc: dict) -> str:
    for s in loc.get("sub_locations", []):
        if s["zh"] == sub_zh:
            return f"{s['en']} ({s['zh']})"
    return sub_zh
