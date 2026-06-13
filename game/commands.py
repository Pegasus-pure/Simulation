## Command parser with alias resolution and tab-completion support.

from dataclasses import dataclass, field

# ── Command registry ──────────────────────────────────────────────

COMMANDS: dict[str, dict] = {
    "help":    {"aliases": ["?"],       "desc": "显示所有可用命令"},
    "where":   {"aliases": ["w"],       "desc": "列出所有可观察地点"},
    "goto":    {"aliases": ["g"],       "desc": "切换观察点到指定地点"},
    "focus":   {"aliases": ["f"],       "desc": "关注特定角色 [Phase 2]"},
    "unfocus": {"aliases": ["uf"],      "desc": "取消所有焦点角色 [Phase 2]"},
    "info":    {"aliases": ["i"],       "desc": "查看角色/地点详细信息 [Phase 2]"},
    "history": {"aliases": ["h", "hi"], "desc": "查看最近N条事件 [Phase 2]"},
    "chain":   {"aliases": ["c"],       "desc": "追踪事件的因果链 [Phase 2]"},
    "world":   {"aliases": ["wr"],      "desc": "世界宏观状态摘要 [Phase 2]"},
    "pause":   {"aliases": ["p"],       "desc": "暂停/恢复世界时间 [Phase 2]"},
    "speed":   {"aliases": ["sp"],      "desc": "设置时间流速 [Phase 2]"},
    "clear":   {"aliases": ["cls"],     "desc": "清屏"},
    "quit":    {"aliases": ["q", "exit"], "desc": "退出游戏"},
}

# ── Alias → canonical lookup table (built once) ──────────────────

_ALIAS_MAP: dict[str, str] = {}
for _cmd, _info in COMMANDS.items():
    _ALIAS_MAP[_cmd] = _cmd
    for _a in _info["aliases"]:
        _ALIAS_MAP[_a] = _cmd


@dataclass(slots=True)
class ParsedCommand:
    """Result of parsing a user input line."""
    command: str       # canonical name, or "unknown"
    raw_name: str      # what the user typed
    args: str          # everything after the command word


def parse(raw_input: str) -> ParsedCommand | None:
    """Parse a raw input string. Returns None for empty input."""
    trimmed = raw_input.strip()
    if not trimmed:
        return None

    parts = trimmed.split(maxsplit=1)
    raw_cmd = parts[0].lower()
    canonical = _ALIAS_MAP.get(raw_cmd, "")
    args = parts[1].strip() if len(parts) > 1 else ""

    if not canonical:
        return ParsedCommand("unknown", raw_cmd, args)

    return ParsedCommand(canonical, raw_cmd, args)


def get_completions(text_before_cursor: str) -> list[str]:
    """Return possible completions for the current input prefix."""
    trimmed: str = text_before_cursor.strip()
    if not trimmed:
        # Empty input — return all command names
        return sorted(list(COMMANDS.keys()))

    parts: list[str] = trimmed.split(maxsplit=1)
    prefix: str = parts[0].lower()

    # If no space yet, try completing the command word
    if len(parts) == 1:
        candidates: list[str] = []
        for cmd, info in COMMANDS.items():
            if cmd.startswith(prefix):
                candidates.append(cmd)
            for a in info["aliases"]:
                if a.startswith(prefix):
                    candidates.append(a)
        return sorted(candidates)

    # After "goto" / "g", complete location names AND sub-location names
    if prefix in ("goto", "g"):
        loc_prefix = parts[1].lower() if len(parts) > 1 else ""
        from game.world_state import LOCATIONS
        candidates: list[str] = []
        for loc_id, loc in LOCATIONS.items():
            if loc_id.startswith(loc_prefix):
                candidates.append(loc_id)
            for sub in loc.get("sub_locations", []):
                if sub["en"].startswith(loc_prefix):
                    candidates.append(sub["en"])
                if sub["zh"].startswith(parts[1].strip() if len(parts) > 1 else ""):
                    candidates.append(sub["zh"])
        return sorted(set(candidates))

    return []


def build_help_text() -> str:
    """Generate a formatted help string."""
    lines: list[str] = [
        "═" * 44,
        "          可用命令",
        "═" * 44,
        "",
    ]
    for cmd, info in COMMANDS.items():
        alias_str = "/".join(info["aliases"])
        lines.append(f"  {cmd:<10} ({alias_str:<8})  {info['desc']}")

    lines += ["", "输入命令缩写或别名也可以。Tab 补全可用。"]
    return "\n".join(lines)
