## Terminal renderer — 3-panel real-time dashboard.
## Uses rich.Layout + Live for auto-refreshing display.
from __future__ import annotations

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from game.world_state import WorldState, LOCATIONS, get_location_name
from game.event_provider import EVENT_COLORS
from game.character import Character

console = Console()

# ── Dashboard ─────────────────────────────────────────────────────

def render_dashboard(world: WorldState, current_loc: str, current_sub: str,
                     focused: set[str], last_cmd: str = "",
                     last_msg: str = "", ai_enabled: bool = False,
                     paused: bool = False) -> Layout:
    """Build a 3-panel rich.Layout for the main game view."""

    root = Layout()
    root.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="input_area", size=4),
    )
    root["body"].split_row(
        Layout(name="world", ratio=1),
        Layout(name="location", ratio=2),
        Layout(name="focus", ratio=1),
    )

    # ── Input area ──
    input_lines: list[str] = []
    if last_cmd:
        input_lines.append(f"[green]> {last_cmd}[/green]")
    if last_msg:
        input_lines.append(f"[yellow]{last_msg}[/yellow]")
    mode = "[cyan]AI[/]" if ai_enabled else "[dim]T[/]"
    pause_str = " [yellow]⏸[/]" if paused else ""
    input_lines.append(f"[bold]{mode}> [/bold][dim]输入命令...[/dim]{pause_str}")
    root["input_area"].update(
        Panel("\n".join(input_lines), border_style="bright_green", height=4))
    war_text = ""
    if world.war_active:
        phases = {"preparation": "备战中", "skirmish": "边境冲突", "battle": "全面会战"}
        phase_cn = phases.get(world.war_phase, world.war_phase)
        war_text = f"  [bold red]⚔ 战争: {phase_cn}[/bold red]"

    header_text = Text()
    header_text.append(f"神域微言 · {world.time_string()}", style="bold white")
    header_text.append(war_text)
    root["header"].update(Panel(header_text, height=3))

    # ── World panel ──
    root["world"].update(_world_panel(world))

    # ── Location panel ──
    root["location"].update(_location_panel(world, current_loc, current_sub))

    # ── Focus panel ──
    root["focus"].update(_focus_panel(world, focused))

    return root


def _world_panel(world: WorldState) -> Panel:
    lines: list[str] = []
    lines.append("[bold]世界状态[/bold]")
    lines.append("")

    # Population
    human_count = len([c for c in world.characters.values()
                       if c.race == "human" and c.status == "alive"])
    demon_count = len([c for c in world.characters.values()
                       if c.race == "demon" and c.status == "alive"])
    lines.append(f"人类: {human_count}人  魔族: {demon_count}人")
    lines.append(f"事件总数: {len(world.all_events)}")
    lines.append("")

    # Location summaries
    for loc_id in ["academy", "front", "throne", "demon", "village"]:
        cnt = len([c for c in world.characters.values()
                   if c.location == loc_id and c.status == "alive"])
        loc_name = LOCATIONS[loc_id]["name"]
        marker = ""
        if world.war_active and loc_id == "front":
            marker = " [red]⚔[/red]"
        lines.append(f"[dim]{loc_name}: {cnt}人{marker}[/dim]")

    # Narrative threads
    if world.narrative_threads:
        lines.append("")
        lines.append("[dim]叙事线:[/dim]")
        for tid, mom in sorted(world.narrative_threads.items(),
                                key=lambda x: -x[1])[:5]:
            bar = "█" * int(mom) + "░" * int(5 - mom) if mom <= 5 else "█" * 5
            lines.append(f"[dim]  {tid}: {bar}[/dim]")

    content = "\n".join(lines)
    return Panel(content, title="🌍", border_style="dim blue", height=25)


def _location_panel(world: WorldState, loc_id: str, sub_filter: str) -> Panel:
    if not loc_id:
        return Panel(
            "\n  输入 [bold]goto [地点][/bold] 开始观察。\n  输入 [bold]where[/bold] 查看所有地点。",
            title="📍 观察", border_style="dim green", height=25)

    loc = LOCATIONS[loc_id]
    lines: list[str] = []
    lines.append(f"[bold]{loc['name']}[/bold]")
    if sub_filter:
        lines.append(f"[cyan]▸ {sub_filter}[/cyan]")
    lines.append(f"[dim]{loc['desc']}[/dim]")
    lines.append("")

    # Characters
    chars = world.get_characters_at(loc_id)
    if chars:
        lines.append("[dim]在场:[/dim] " + ", ".join(c.name for c in chars))
    lines.append("")

    # Events
    recent = [e for e in world.all_events[-60:]
              if e.get("location") == loc_id]
    if sub_filter:
        recent = [e for e in recent if e.get("sub_location") == sub_filter]

    for ev in recent[-12:]:
        color = EVENT_COLORS.get(ev.get("priority", "daily"), "white")
        lines.append(f"[{color}]{ev['text']}[/{color}]")

    if not recent:
        lines.append("[dim]（等待事件...）[/dim]")

    content = "\n".join(lines)
    return Panel(content, title="📍 观察", border_style="dim green", height=25)


def _focus_panel(world: WorldState, focused: set[str]) -> Panel:
    lines: list[str] = []
    lines.append("[bold]关注[/bold]")
    lines.append("")

    if not focused:
        lines.append("[dim]输入 [bold]focus [名字][/bold]")
        lines.append("关注角色。")
        lines.append("")
        lines.append("[dim]无参可列出可关注角色。[/dim]")
        return Panel("\n".join(lines), title="👁 聚焦", border_style="dim yellow", height=25)

    for name in list(focused)[:3]:
        matches = [c for c in world.characters.values()
                   if c.name == name]
        if not matches:
            continue
        ch = matches[0]
        lines.append(f"[bold cyan]● {ch.name}[/bold cyan]")
        lines.append(f"  {ch.role or ch.race}  {ch.race}")
        lines.append(f"  战力: {_mini_bar(ch.combat)}")
        lines.append(f"  魔力: {_mini_bar(ch.magic)}")
        lines.append(f"  意志: {_mini_bar(ch.will)}")
        lines.append(f"  社交: {_mini_bar(ch.social)}")
        loc_name = get_location_name(ch.location)
        lines.append(f"  位置: {loc_name}")
        lines.append("")

    if len(focused) > 3:
        lines.append(f"[dim]...还有 {len(focused)-3} 个关注[/dim]")

    content = "\n".join(lines)
    return Panel(content, title="👁 聚焦", border_style="dim yellow", height=25)


def _mini_bar(val: int, width: int = 12) -> str:
    filled = int(val / 100 * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {val}"


# ── Popup views (cleared by help/where/info/focus, dismissed with Enter) ──

def render_char_list(chars: list[Character]) -> None:
    console.print()
    console.print("[dim]  ┌─ 当前场景角色 ─────────────────────────────┐[/dim]")
    for ch in chars:
        console.print(f"  │  [bold]{ch.name:<8}[/bold] {ch.role or ch.race:<8} 战力{ch.combat:>3} 魔力{ch.magic:>3}")
    console.print("[dim]  └──────────────────────────────────────────────┘[/dim]")
    console.print("  [dim]输入 info [名字] 查看详情。[/dim]")
    console.print()


def render_char_detail(ch: Character) -> None:
    table = Table(title=ch.name, show_header=False, box=None, padding=(0, 2))
    table.add_column("attr", style="dim", width=8)
    table.add_column("val", width=30)
    loc_name = get_location_name(ch.location)
    table.add_row("种族", ch.race)
    table.add_row("年龄", str(ch.age))
    table.add_row("出身", ch.origin)
    table.add_row("身份", ch.role or "—")
    table.add_row("地点", loc_name)
    table.add_row("战力", _bar(ch.combat))
    table.add_row("魔力", _bar(ch.magic))
    table.add_row("战术", _bar(ch.tactics))
    table.add_row("智慧", _bar(ch.wisdom))
    table.add_row("意志", _bar(ch.will))
    table.add_row("社交", _bar(ch.social))
    console.print(table)
    console.print()


def render_focus_list(focused: set[str]) -> None:
    console.print()
    if focused:
        console.print(f"  [cyan]当前关注: {', '.join(focused)}[/cyan]")
        console.print("  [dim]输入 unfocus [名字] 取消关注。[/dim]")
    else:
        console.print("  [dim]当前未关注任何角色。[/dim]")
        console.print("  [dim]输入 focus [名字] 关注角色。[/dim]")
    console.print()


def _bar(val: int, width: int = 20) -> str:
    filled = int(val / 100 * width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {val}"


# ── Prompt (below dashboard) ──────────────────────────────────────

def prompt(ai_enabled: bool, paused: bool) -> str:
    mode = "[cyan]AI[/]" if ai_enabled else "[dim]T[/]"
    pause_indicator = " [yellow]⏸[/]" if paused else ""
    return console.input(f"[bold green]{mode}> [/bold green]")
