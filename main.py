#!/usr/bin/env python3
"""神域微言 v0.5.0 — pygame 3-row dashboard.
   Row 1: World | Location | Focus
   Row 2: Command log
   Row 3: Input bar
   Run: python main.py"""

import sys, os, threading, time
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.config import Config
from game.world_state import WorldState, LOCATION_IDS
from game.event_provider import EventProvider, TemplateProvider, AIProvider
from game.commands import parse
from game.handlers import CommandHandler
from game.academy import AcademySystem
from game.war_system import WarSystem
from game.narrative import NarrativeEngine
from game.ui_pg import UI, FPS

# ── Globals ───────────────────────────────────────────────────────

config: Config = Config.load()
world: WorldState = WorldState()
provider: EventProvider | None = None
handler: CommandHandler | None = None
_running: bool = True
_paused: bool = False


# ── Colour constants for log ──────────────────────────────────────

LOG_GREEN  = 0x00E65A
LOG_YELLOW = 0xE6BE28
LOG_CYAN   = 0x28D2D2
LOG_RED    = 0xE63C3C
LOG_DIM    = 0x82828C


# ── Provider ──────────────────────────────────────────────────────

def setup_provider() -> EventProvider:
    if config.ai_enabled:
        return AIProvider(config.api_key, config.api_base, config.api_model)
    return TemplateProvider()


# ── Background event thread ───────────────────────────────────────

def event_loop() -> None:
    while _running:
        time.sleep(config.tick_interval_ms / 1000.0)
        if _paused:
            continue
        world.advance_time()
        NarrativeEngine.decay_all(world)
        for text in AcademySystem.tick(world):
            _inject(text, "academy", "academy_system", "development")
        for text in WarSystem.tick(world):
            _inject(text, "front", "war_system", "conflict")
        for loc_id in LOCATION_IDS:
            ev = provider.generate(world, loc_id)
            if ev:
                world.all_events.append(ev)
                world.event_log.append(ev["text"])
        if len(world.event_log) > 100:
            world.event_log = world.event_log[-100:]


def _inject(text: str, location: str, category: str, priority: str) -> None:
    world.all_events.append({
        "text": text, "priority": priority,
        "location": location, "sub_location": location,
        "category": category,
    })
    world.event_log.append(text)


# ── Main ──────────────────────────────────────────────────────────

def main() -> None:
    global provider, handler, _running, _paused

    # Load world
    save_path = os.path.join(os.path.dirname(__file__), "save.json")
    if os.path.exists(save_path):
        try:
            loaded = WorldState.load(save_path)
            for k, v in loaded.__dict__.items():
                setattr(world, k, v)
        except Exception:
            world.load_initial()
    else:
        world.load_initial()

    provider = setup_provider()
    handler = CommandHandler(world, config)

    threading.Thread(target=event_loop, daemon=True).start()

    # ── UI ────────────────────────────────────────────────────────
    ui = UI()
    input_text: str = ""
    log: list[tuple[str, int]] = []  # (text, color_int)

    def add_log(text: str, color: int) -> None:
        log.append((text, color))
        if len(log) > 50:
            del log[0]

    add_log("神域微言 v0.5.0 — 输入 help 查看命令", LOG_DIM)

    while _running:
        ui.clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                handler._quit()
                return

            if event.type == pygame.TEXTINPUT:
                if len(input_text) < 80:
                    input_text += event.text
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    raw = input_text.strip()
                    if raw:
                        add_log(f"> {raw}", LOG_GREEN)
                    input_text = ""

                    if not raw:
                        continue

                    cmd = parse(raw)
                    if cmd is None:
                        continue

                    if cmd.command == "pause":
                        _paused = not _paused
                        add_log("世界已暂停" if _paused else "世界已恢复", LOG_YELLOW)
                        continue

                    if cmd.command == "quit":
                        handler._quit()
                        return

                    handler.dispatch(cmd)

                    # Log result
                    msg = handler._last_message
                    if msg:
                        color = LOG_YELLOW
                        if "错误" in msg or "未找到" in msg or "未知" in msg:
                            color = LOG_RED
                        elif "关注" in msg or "取消" in msg:
                            color = LOG_CYAN
                        add_log(f"  {msg}", color)

                    # Popup handlers return popup lines — log them
                    if handler.popup_lines:
                        for pl in handler.popup_lines[:8]:
                            add_log(f"  {pl}", LOG_DIM)
                        handler.clear_popup()

                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_ESCAPE:
                    input_text = ""

        ui.render(world, handler.current_loc, handler.current_sub,
                  handler.focused, input_text, log,
                  config.ai_enabled, _paused)


if __name__ == "__main__":
    main()
