## Event generation — abstract interface + Template + AI implementations.
## TemplateProvider: local, offline, no API needed.
## AIProvider: OpenAI-compatible API for richer narrative.
from __future__ import annotations

import abc
import json
import os
import random
from typing import Any

from game.character import Character
from game.world_state import LOCATIONS, WorldState
from game.narrative import NarrativeEngine

DATA_DIR: str = os.path.join(os.path.dirname(__file__), "data")


def _random_sub(loc_id: str) -> str:
    """Pick a random sub-location zh name from a location."""
    subs = LOCATIONS.get(loc_id, {}).get("sub_locations", [])
    if not subs:
        return "?"
    return random.choice(subs)["zh"]

# ── Colour constants for terminal output ────────────────────────
EVENT_COLORS: dict[str, str] = {
    "daily":       "dim white",
    "development": "white",
    "conflict":    "red",
    "turning":     "bold yellow",
}


# ── Abstract base ─────────────────────────────────────────────────

class EventProvider(abc.ABC):
    """Generates an event given the current world snapshot."""

    @abc.abstractmethod
    def generate(self, world: WorldState, for_location: str) -> dict | None:
        """Return an event dict or None if nothing to generate.
        Event dict: {text, priority, location, sub_location, category, causal_parent}
        """
        ...


# ── Template provider (no AI) ─────────────────────────────────────

class TemplateProvider(EventProvider):
    """Conditional template matching with variable filling.
    Uses a simple state machine to chain events into narrative arcs."""

    def __init__(self) -> None:
        self._templates: list[dict] = []
        self._load_templates()

    def _load_templates(self) -> None:
        path = os.path.join(DATA_DIR, "templates.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._templates = json.load(f)

    def generate(self, world: WorldState, for_location: str) -> dict | None:
        if not self._templates:
            return self._fallback_event(world, for_location)

        # 1. Collect candidates that pass condition gates
        candidates: list[tuple[dict, float]] = []
        location_chars = world.get_characters_at(for_location)

        for tmpl in self._templates:
            if not self._check_conditions(tmpl, world, for_location, location_chars):
                continue
            score = self._score_template(tmpl, world)
            candidates.append((tmpl, score))

        if not candidates:
            return self._fallback_event(world, for_location)

        # 2. Weighted random selection
        total = sum(s for _, s in candidates)
        r = random.uniform(0, total)
        cumulative = 0.0
        chosen = candidates[0][0]
        for tmpl, score in candidates:
            cumulative += score
            if r <= cumulative:
                chosen = tmpl
                break

        # 3. Fill variables
        event = self._fill_template(chosen, world, for_location, location_chars)

        # 4. Update narrative state via NarrativeEngine
        hints: list[str] = chosen.get("next_hints", [])
        NarrativeEngine.add_hints(world, hints)
        for h in hints:
            NarrativeEngine.boost_thread(world, h, amount=0.6)

        # 5. Apply outcome effects
        self._apply_effects(chosen, world, location_chars)

        return event

    def _check_conditions(self, tmpl: dict, world: WorldState,
                          loc: str, chars: list[Character]) -> bool:
        """Check require/forbid conditions."""
        req: list[str] = tmpl.get("require", [])
        for r in req:
            if r == "has_chars" and len(chars) == 0:
                return False
            if r == "min_2_chars" and len(chars) < 2:
                return False
            if r == "has_rivalry":
                if not any(c.narrative_tags for c in chars):
                    return False
        forbid: list[str] = tmpl.get("forbid", [])
        # Phase 2: forbids are optional
        return True

    def _score_template(self, tmpl: dict, world: WorldState) -> float:
        base: float = float(tmpl.get("weight", 3.0))
        hints: list[str] = tmpl.get("next_hints", [])
        for h in hints:
            if h in world.last_hints:
                base *= 2.5
            moment = world.narrative_threads.get(h, 0.0)
            base += moment * 2.0
        return max(base, 0.3)

    def _fill_template(self, tmpl: dict, world: WorldState,
                       loc: str, chars: list[Character]) -> dict:
        text = tmpl["text_template"]
        subs: dict[str, str] = {}

        for var_name, var_spec in tmpl.get("variables", {}).items():
            val = self._resolve_variable(var_spec, chars)
            subs[var_name] = val

        try:
            text = text.format(**subs)
        except KeyError:
            pass

        sub_loc = _random_sub(loc)
        return {
            "text": f"[{sub_loc}] {text}",
            "priority": tmpl.get("priority", "daily"),
            "location": loc,
            "sub_location": sub_loc,
            "category": tmpl.get("category", "daily"),
        }

    def _resolve_variable(self, spec: dict, chars: list[Character]) -> str:
        role = spec.get("role", "any")
        pool_vals: list[str] = spec.get("pool", [])

        if role == "random_char" and chars:
            return random.choice(chars).name
        if role == "char_pair_a" and len(chars) >= 2:
            return chars[0].name
        if role == "char_pair_b" and len(chars) >= 2:
            return chars[1].name
        if role == "random_pool" and pool_vals:
            return random.choice(pool_vals)
        if role == "location_name":
            return LOCATIONS.get(chars[0].location if chars else "academy", {}).get("name", "某地")

        return spec.get("default", "某人")

    def _apply_effects(self, tmpl: dict, world: WorldState,
                       chars: list[Character]) -> None:
        effects: list[dict] = tmpl.get("effects", [])
        for eff in effects:
            target = eff.get("target", "")
            field = eff.get("field", "")
            delta = eff.get("delta", 0)
            if target == "random_char" and chars:
                ch = random.choice(chars)
                if hasattr(ch, field):
                    setattr(ch, field, min(100, max(0, getattr(ch, field) + delta)))
            if target == "char_a" and len(chars) >= 1:
                ch = chars[0]
                if hasattr(ch, field):
                    setattr(ch, field, min(100, max(0, getattr(ch, field) + delta)))

    def _fallback_event(self, world: WorldState, loc: str) -> dict | None:
        """When no template matches, generate a minimal event."""
        chars = world.get_characters_at(loc)
        sub = _random_sub(loc)
        if chars:
            ch = random.choice(chars)
            text = f"[{sub}] {ch.name} 静静地待着。"
        else:
            text = f"[{sub}] 此处一片寂静。"
        return {"text": text, "priority": "daily", "location": loc,
                "sub_location": sub, "category": "daily"}


# ── AI provider (OpenAI-compatible) ───────────────────────────────

class AIProvider(EventProvider):
    """Generates events via OpenAI-compatible API."""

    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1",
                 model: str = "gpt-4o-mini") -> None:
        self._key = api_key
        self._base = api_base.rstrip("/")
        self._model = model

    def generate(self, world: WorldState, for_location: str) -> dict | None:
        import urllib.request
        import urllib.error

        prompt = self._build_prompt(world, for_location)

        body = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 200,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError):
            return None  # Fall back to template

        lines = [l for l in content.split("\n") if l.strip()]
        if not lines:
            return None

        sub = _random_sub(for_location)
        text = f"[{sub}] {lines[0]}"
        return {
            "text": text, "priority": "daily", "location": for_location,
            "sub_location": sub, "category": "ai_generated",
        }

    def _build_prompt(self, world: WorldState, for_location: str) -> str:
        loc = LOCATIONS.get(for_location, {})
        chars = world.get_characters_at(for_location)
        char_info = "; ".join(
            f"{c.name}({c.role or c.race}, 战力{c.combat} 智慧{c.wisdom})"
            for c in chars[:5]
        )
        recent = world.event_log[-3:] if world.event_log else ["（无）"]
        recent_str = " | ".join(recent)

        return (
            f"时间: {world.time_string()}\n"
            f"地点: {loc.get('name', for_location)} — {loc.get('desc', '')}\n"
            f"在此的角色: {char_info or '无人'}\n"
            f"最近事件: {recent_str}\n"
            f"请用一句中文描述接下来在这个地点发生的一件合理的事情。"
            f"要有叙事感，不要超过50字。"
        )


SYSTEM_PROMPT = """你是一个奇幻世界的叙事引擎。
世界设定：人类与魔族共存，有魔法、有勇者学院、有战争。
请根据给定的世界状态生成合理、有因果逻辑的事件。
只用一句中文描述，不要解释，不要标记。"""
