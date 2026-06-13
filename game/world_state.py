## Dynamic world state — replaces Phase 1's hardcoded world.py.
## Manages characters, locations, event history, and the game clock.
from __future__ import annotations

import json
import os
import random
from typing import Any

from game.character import Character

DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")


# ── Location definitions ──────────────────────────────────────────

LOCATIONS: dict[str, dict[str, Any]] = {
    "academy": {
        "id": "academy", "name": "academy (皇家勇者学院)", "name_zh": "皇家勇者学院",
        "type": "academy",
        "desc": "培养勇者与贤者的学府。剑术与魔法在此传承。",
        "sub_locations": [
            {"zh": "讲堂", "en": "lecture_hall"},
            {"zh": "训练场", "en": "training_ground"},
            {"zh": "宿舍", "en": "dormitory"},
            {"zh": "院长室", "en": "dean_office"},
        ],
    },
    "throne": {
        "id": "throne", "name": "throne (王座厅)", "name_zh": "王座厅",
        "type": "political",
        "desc": "北境王国的权力中枢。命运在此被一言而定。",
        "sub_locations": [
            {"zh": "王座厅", "en": "main_hall"},
            {"zh": "侧厅", "en": "side_hall"},
        ],
    },
    "front": {
        "id": "front", "name": "front (铁门关前线)", "name_zh": "铁门关前线",
        "type": "military",
        "desc": "人类王国与魔族领地之间的最后屏障。",
        "sub_locations": [
            {"zh": "城墙", "en": "wall"},
            {"zh": "军营", "en": "barracks"},
            {"zh": "伤兵营", "en": "infirmary"},
            {"zh": "指挥部", "en": "command_post"},
        ],
    },
    "demon": {
        "id": "demon", "name": "demon (深渊裂缝·魔族领地)", "name_zh": "深渊裂缝",
        "type": "demon",
        "desc": "暗影与魔力的源头。魔族在此繁衍生息，眺望着人类的世界。",
        "sub_locations": [
            {"zh": "战争议会", "en": "war_council"},
            {"zh": "深渊边缘", "en": "abyss_edge"},
            {"zh": "部落营地", "en": "tribe_camp"},
        ],
    },
    "village": {
        "id": "village", "name": "village (石炉村)", "name_zh": "石炉村",
        "type": "village",
        "desc": "一个普通的边境村庄。普通人在这里过着普通的生活——直到战争改变一切。",
        "sub_locations": [
            {"zh": "村口", "en": "village_gate"},
            {"zh": "酒馆", "en": "tavern"},
            {"zh": "田间", "en": "fields"},
        ],
    },
}

LOCATION_IDS = list(LOCATIONS.keys())

# Build sub-location maps (zh → parent, en → parent)
SUB_LOCATION_MAP: dict[str, str] = {}
SUB_LOCATION_EN_MAP: dict[str, str] = {}
for _loc_id, _loc_data in LOCATIONS.items():
    for _sub in _loc_data.get("sub_locations", []):
        SUB_LOCATION_MAP[_sub["zh"]] = _loc_id
        SUB_LOCATION_EN_MAP[_sub["en"]] = _loc_id


def resolve_location(target: str) -> str | None:
    """Resolve a location name (zh, en, or canonical ID). Returns parent location ID."""
    t = target.strip().lower().replace(" ", "")
    if t in LOCATIONS:
        return t
    # Match by Chinese sub name
    if t in SUB_LOCATION_MAP:
        return SUB_LOCATION_MAP[t]
    # Match by English sub name
    if t in SUB_LOCATION_EN_MAP:
        return SUB_LOCATION_EN_MAP[t]
    # Partial match on English sub-location names
    for en, parent in SUB_LOCATION_EN_MAP.items():
        if en.startswith(t):
            return parent
    return None


def get_location_name(loc_id: str) -> str:
    """Get the display name for a location ID."""
    return LOCATIONS.get(loc_id, {}).get("name", loc_id)


# ── World State ────────────────────────────────────────────────────

class WorldState:
    """The entire mutable state of the simulated world."""

    def __init__(self) -> None:
        self.characters: dict[str, Character] = {}
        self.event_log: list[str] = []       # recent event texts
        self.all_events: list[dict] = []      # full event history with metadata
        self.year: int = 3
        self.season: str = "秋"
        self.day: int = 1
        self.hour: int = 8
        self.minute: int = 0
        self.tick_count: int = 0
        self.narrative_threads: dict[str, float] = {}  # thread_id → momentum
        self.last_hints: list[str] = []
        # War state
        self.war_active: bool = False
        self.war_phase: str = ""       # "preparation" | "skirmish" | "battle" | outcome
        self.war_tick_start: int = 0
        self.war_side_advantage: str = ""  # "human" | "demon"

    def load_initial(self) -> None:
        """Load characters from JSON data file."""
        path = os.path.join(DATA_DIR, "characters.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Character data not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for cd in data["characters"]:
            ch = Character.from_dict(cd)
            self.characters[ch.id] = ch

    def get_characters_at(self, location_id: str) -> list[Character]:
        return [c for c in self.characters.values() if c.location == location_id and c.status == "alive"]

    def time_string(self) -> str:
        return f"纪元{self.year}年·{self.season}·第{self.day}日"

    def advance_time(self) -> None:
        """Advance by one simulated minute."""
        self.minute += 1
        self.tick_count += 1
        if self.minute >= 60:
            self.minute = 0
            self.hour += 1
        if self.hour >= 24:
            self.hour = 0
            self.day += 1
        if self.day > 90:
            self.day = 1
            self._next_season()

    def _next_season(self) -> None:
        seasons = ["春", "夏", "秋", "冬"]
        idx = seasons.index(self.season)
        if idx == 3:
            self.year += 1
            self.season = seasons[0]
        else:
            self.season = seasons[idx + 1]

    def to_dict(self) -> dict:
        return {
            "year": self.year, "season": self.season, "day": self.day,
            "hour": self.hour, "minute": self.minute, "tick_count": self.tick_count,
            "characters": [c.to_dict() for c in self.characters.values()],
            "all_events": self.all_events[-200:],
            "narrative_threads": dict(self.narrative_threads),
            "last_hints": list(self.last_hints),
            "war_active": self.war_active, "war_phase": self.war_phase,
            "war_tick_start": self.war_tick_start, "war_side_advantage": self.war_side_advantage,
        }

    @staticmethod
    def from_dict(d: dict) -> WorldState:
        ws = WorldState()
        ws.year = d.get("year", 3)
        ws.season = d.get("season", "秋")
        ws.day = d.get("day", 1)
        ws.hour = d.get("hour", 8)
        ws.minute = d.get("minute", 0)
        ws.tick_count = d.get("tick_count", 0)
        ws.all_events = d.get("all_events", [])
        ws.narrative_threads = d.get("narrative_threads", {})
        ws.last_hints = d.get("last_hints", [])
        ws.war_active = d.get("war_active", False)
        ws.war_phase = d.get("war_phase", "")
        ws.war_tick_start = d.get("war_tick_start", 0)
        ws.war_side_advantage = d.get("war_side_advantage", "")
        for cd in d.get("characters", []):
            ch = Character.from_dict(cd)
            ws.characters[ch.id] = ch
        return ws

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(path: str) -> WorldState:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Save file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return WorldState.from_dict(data)
