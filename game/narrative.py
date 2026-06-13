## Narrative state machine — thread tracking, momentum, arc completion.
## Drives template selection so events form coherent story chains.
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world_state import WorldState


class NarrativeEngine:
    """Tracks narrative threads across the world simulation.
    Each thread has momentum that decays over time, biasing template selection
    toward continuing existing story arcs."""

    MOMENTUM_DECAY: float = 0.85       # per tick when no matching event
    MAX_MOMENTUM: float = 5.0
    NEW_THREAD_CHANCE: float = 0.15    # chance to start a fresh thread instead of continuing

    @staticmethod
    def boost_thread(world: WorldState, thread_id: str, amount: float = 0.8) -> None:
        """Add momentum to a narrative thread."""
        current = world.narrative_threads.get(thread_id, 0.0)
        world.narrative_threads[thread_id] = min(current + amount, NarrativeEngine.MAX_MOMENTUM)

    @staticmethod
    def decay_all(world: WorldState) -> None:
        """Apply decay to all threads each tick."""
        for tid in list(world.narrative_threads.keys()):
            world.narrative_threads[tid] *= NarrativeEngine.MOMENTUM_DECAY
            if world.narrative_threads[tid] < 0.1:
                del world.narrative_threads[tid]

    @staticmethod
    def pick_thread(world: WorldState, hints: list[str]) -> str | None:
        """Given a list of possible next_hints, pick the best thread to continue.
        Returns the thread ID if continuing, or None to start fresh."""
        if not hints:
            return None

        # Find the highest-momentum thread that matches any hint
        best: tuple[str, float] = ("", 0.0)
        for hint in hints:
            m = world.narrative_threads.get(hint, 0.0)
            if m > best[1]:
                best = (hint, m)

        if best[1] > 0.5:
            return best[0]
        return None

    @staticmethod
    def add_hints(world: WorldState, hints: list[str]) -> None:
        """Record hints as the last-seen narrative directions."""
        world.last_hints = hints

    @staticmethod
    def complete_arc(world: WorldState, thread_id: str) -> None:
        """Mark a narrative thread as complete — remove it and log."""
        world.narrative_threads.pop(thread_id, None)
        world.last_hints = [h for h in world.last_hints if h != thread_id]


# ── Pre-defined narrative arcs ─────────────────────────────────────

NARRATIVE_ARCS: dict[str, dict] = {
    "rivalry_karl_leon": {
        "name": "卡尔vs列昂",
        "stages": ["rivalry_ignite", "rivalry_escalate", "rivalry_climax", "rivalry_resolve"],
        "characters": ["karl", "leon"],
        "location": "academy",
    },
    "prodigy_eileen": {
        "name": "天才艾琳",
        "stages": ["prodigy_discover", "prodigy_pressure", "prodigy_breakthrough"],
        "characters": ["eileen"],
        "location": "academy",
    },
    "mentor_hawk_karl": {
        "name": "霍克与卡尔",
        "stages": ["mentor_notice", "mentor_private_lesson", "mentor_legacy"],
        "characters": ["karl"],
        "location": "academy",
    },
    "demon_war_debate": {
        "name": "魔族战争辩论",
        "stages": ["demon_observe", "demon_debate", "demon_decision"],
        "characters": ["demon_gorm", "demon_cautious"],
        "location": "demon",
    },
    "border_tension": {
        "name": "边境紧张",
        "stages": ["border_watch", "border_skirmish", "border_war"],
        "characters": ["general_hal", "guard_captain"],
        "location": "front",
    },
}
