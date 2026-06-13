## Command handlers — stateless command logic, state-only mutations.
## Terminal rendering is handled by the Live dashboard in main.py.
from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from game.config import Config
from game.world_state import WorldState, LOCATIONS, get_location_name, resolve_location
from game.commands import build_help_text
from game import terminal

if TYPE_CHECKING:
    from game.commands import ParsedCommand


class CommandHandler:
    """Holds runtime state. Commands mutate state; dashboard auto-refreshes."""

    def __init__(self, world: WorldState, config: Config) -> None:
        self.world = world
        self.config = config
        self.current_loc: str = ""
        self.current_sub: str = ""
        self.focused: set[str] = set()
        self._last_message: str = ""
        self._popup_title: str = ""
        self._popup_lines: list[str] = []

    @property
    def popup_title(self) -> str:
        return self._popup_title

    @property
    def popup_lines(self) -> list[str]:
        return self._popup_lines

    def clear_popup(self) -> None:
        self._popup_title = ""
        self._popup_lines = []  # one-line feedback for the input area

    # ── Dispatch ──────────────────────────────────────────────────

    def dispatch(self, cmd: ParsedCommand) -> None:
        self._last_message = ""
        match cmd.command:
            case "help":    self._help()
            case "where":   self._where()
            case "goto":    self._goto(cmd.args)
            case "info":    self._info(cmd.args)
            case "focus":   self._focus(cmd.args)
            case "unfocus": self._unfocus(cmd.args)
            case "clear":   pass  # no-op in dashboard mode
            case "quit":    self._quit()
            case "api":     self._api(cmd.args)
            case _:
                self._last_message = f"未知命令: {cmd.raw_name}"

    # ── help ──────────────────────────────────────────────────────

    def _help(self) -> None:
        text = build_help_text()
        self._popup_title = "可用命令"
        self._popup_lines = text.split("\n")

    # ── where ─────────────────────────────────────────────────────

    def _where(self) -> None:
        lines: list[str] = []
        lines.append("")
        for loc_id, loc in LOCATIONS.items():
            marker = ">" if loc_id == self.current_loc else " "
            cnt = len(self.world.get_characters_at(loc_id))
            lines.append(f"  {marker} {loc['name']}  ({cnt}人)")
            if loc_id == self.current_loc:
                for sub in loc.get("sub_locations", []):
                    sm = "  >" if sub["zh"] == self.current_sub else "    "
                    lines.append(f"  {sm} {sub['en']} ({sub['zh']})")
        lines.append("")
        self._popup_title = "可观察地点"
        self._popup_lines = lines

    # ── goto ──────────────────────────────────────────────────────

    def _goto(self, args: str) -> None:
        target = args.strip()
        if not target:
            # Show available locations
            terminal.console.clear()
            terminal.console.print()
            terminal.console.print("[dim]  ┌─ 可用地点 ────────────────────────────────┐[/dim]")
            for loc_id, loc in LOCATIONS.items():
                terminal.console.print(f"  │  [bold]{loc_id:<12}[/bold]  {loc['name']}")
            terminal.console.print("[dim]  └──────────────────────────────────────────────┘[/dim]")
            terminal.console.print("  [dim]也可输入子地点名，如: goto 讲堂[/dim]")
            terminal.console.print()
            terminal.console.input("按 Enter 返回仪表盘...")
            terminal.console.clear()
            return

        loc_id = resolve_location(target)
        if loc_id is None:
            self._last_message = f"未知地点: '{target}'"
            return

        sub_filter = ""
        if loc_id != target.strip().lower().replace(" ", ""):
            # User typed a sub-location name — resolve to zh form
            sub_filter = _resolve_sub_name(target.strip(), loc_id)

        self.current_loc = loc_id
        self.current_sub = sub_filter
        loc_name = get_location_name(loc_id)
        msg = f"已切换到: {loc_name}"
        if sub_filter:
            msg += f" > {sub_filter}"
        self._last_message = msg

    # ── info ──────────────────────────────────────────────────────

    def _info(self, args: str) -> None:
        name = args.strip()
        chars = self.world.get_characters_at(self.current_loc) if self.current_loc else []

        if not name:
            if not chars:
                self._last_message = "当前场景没有角色"
                return
            lines: list[str] = []
            for ch in chars:
                lines.append(f"  {ch.name:<24}  {ch.role or ch.race:<12}  战力{ch.combat:>3}  魔力{ch.magic:>3}")
            lines.append("")
            lines.append("输入 info [名字] 查看详情。")
            self._popup_title = "当前场景角色"
            self._popup_lines = lines
            return

        matches = [c for c in self.world.characters.values()
                   if name.lower() in c.name.lower()]
        if not matches:
            self._last_message = f"未找到角色: '{name}'"
            return

        lines: list[str] = []
        for ch in matches[:3]:
            from game.world_state import get_location_name
            lines.append(f"  {ch.name}  {ch.race}  {ch.role or ''}")
            lines.append(f"  战力: {'#' * (ch.combat // 10)}{'-' * (10 - ch.combat // 10)} {ch.combat}")
            lines.append(f"  魔力: {'#' * (ch.magic // 10)}{'-' * (10 - ch.magic // 10)} {ch.magic}")
            lines.append(f"  战术: {'#' * (ch.tactics // 10)}{'-' * (10 - ch.tactics // 10)} {ch.tactics}")
            lines.append(f"  智慧: {'#' * (ch.wisdom // 10)}{'-' * (10 - ch.wisdom // 10)} {ch.wisdom}")
            lines.append(f"  意志: {'#' * (ch.will // 10)}{'-' * (10 - ch.will // 10)} {ch.will}")
            lines.append(f"  社交: {'#' * (ch.social // 10)}{'-' * (10 - ch.social // 10)} {ch.social}")
            lines.append(f"  位置: {get_location_name(ch.location)}")
            lines.append("")
        self._popup_title = "角色详情"
        self._popup_lines = lines

    # ── focus ─────────────────────────────────────────────────────

    def _focus(self, args: str) -> None:
        name = args.strip()
        chars = self.world.get_characters_at(self.current_loc) if self.current_loc else []

        if not name:
            terminal.console.clear()
            from game.terminal import render_focus_list
            render_focus_list(self.focused)
            if chars:
                terminal.console.print("[dim]  当前场景可关注:[/dim]")
                for ch in chars:
                    mark = " ●" if ch.name in self.focused else "  "
                    terminal.console.print(f"  {mark} [dim]{ch.name}[/dim]")
            terminal.console.print()
            terminal.console.input("按 Enter 返回仪表盘...")
            terminal.console.clear()
            return

        matches = [c for c in self.world.characters.values()
                   if name.lower() in c.name.lower()]
        if not matches:
            self._last_message = f"未找到角色: '{name}'"
            return

        ch = matches[0]
        if ch.name in self.focused:
            self._last_message = f"已在关注 {ch.name}"
            return

        self.focused.add(ch.name)
        self._last_message = f"● 开始关注 {ch.name}"

    # ── unfocus ───────────────────────────────────────────────────

    def _unfocus(self, args: str) -> None:
        name = args.strip()
        if not name:
            if not self.focused:
                self._last_message = "未关注任何角色"
                return
            count = len(self.focused)
            self.focused.clear()
            self._last_message = f"已取消全部 {count} 个关注"
            return

        removed = None
        for fname in list(self.focused):
            if name.lower() in fname.lower():
                removed = fname
                self.focused.discard(fname)
                break

        if removed:
            self._last_message = f"已取消关注 {removed}"
        else:
            self._last_message = f"未在关注: '{name}'"

    # ── quit ──────────────────────────────────────────────────────

    def _quit(self) -> None:
        save_path = os.path.join(os.path.dirname(__file__), "..", "save.json")
        self.world.save(save_path)
        terminal.console.clear()
        terminal.console.print()
        terminal.console.print("[dim]" + "═" * 50 + "[/dim]")
        terminal.console.print("  [dim]世界已保存。下次再见。[/dim]")
        terminal.console.print("[dim]" + "═" * 50 + "[/dim]")
        terminal.console.print()
        sys.exit(0)

    # ── api ───────────────────────────────────────────────────────

    def _api(self, args: str) -> None:
        parts = args.strip().split(maxsplit=1)
        sub = parts[0].lower() if parts else ""
        value = parts[1] if len(parts) > 1 else ""

        if not sub:
            status = "已启用" if self.config.ai_enabled else "未配置"
            self._last_message = f"API: {status}"
            return

        if sub == "set":
            self.config.set_api(value or "", self.config.api_base, self.config.api_model)
            self._last_message = f"API {'启用' if self.config.ai_enabled else '关闭'}"
        elif sub == "base":
            self.config.set_api(self.config.api_key, value, self.config.api_model)
            self._last_message = f"端点: {value}"
        elif sub == "model":
            self.config.set_api(self.config.api_key, self.config.api_base, value)
            self._last_message = f"模型: {value}"
        else:
            self._last_message = "用法: api set|base|model [值]"


# ── Helpers ───────────────────────────────────────────────────────

def _resolve_sub_name(raw: str, loc_id: str) -> str:
    """Given a user-typed sub-location name, return its zh form for filtering."""
    t = raw.lower().replace(" ", "")
    loc = LOCATIONS.get(loc_id, {})
    for sub in loc.get("sub_locations", []):
        if t == sub["zh"].lower().replace(" ", ""):
            return sub["zh"]
        if t == sub["en"]:
            return sub["zh"]
        if sub["en"].startswith(t):
            return sub["zh"]
    return raw  # fallback
