## War system — organic trigger conditions, phase progression, academy linkage.
## War doesn't "start because it's time" — it starts because conditions ripen.
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world_state import WorldState


# ── Constants ──────────────────────────────────────────────────────

WAR_CHECK_INTERVAL: int = 60  # ticks between war trigger checks (~3 min real time)


class WarSystem:
    """Manages war detection, phase progression, and cross-system effects."""

    @staticmethod
    def tick(world: WorldState) -> list[str]:
        """Each tick, check if war conditions have ripened or if war is progressing."""
        events: list[str] = []

        # Only check periodically
        if world.tick_count % WAR_CHECK_INTERVAL != 0:
            return events

        # ── If not at war, check trigger conditions ──
        if not world.war_active:
            if WarSystem._check_triggers(world):
                events += WarSystem._start_war(world)
        else:
            # ── War is active — progress phases ──
            events += WarSystem._progress_war(world)

        return events

    @staticmethod
    def _check_triggers(world: WorldState) -> bool:
        """Check if conditions are ripe for war to start."""

        # Human unrest factors
        human_factors: int = 0
        # Noble greed: check if any nobles exist
        nobles = [c for c in world.characters.values()
                  if c.origin == "noble" and c.location == "throne" and c.status == "alive"]
        if len(nobles) >= 1:
            human_factors += 1

        # King prestige: check king's will
        king = world.characters.get("king_alvin")
        if king and king.will < 60:
            human_factors += 1

        # Border defense: check front characters
        front_chars = world.get_characters_at("front")
        if len(front_chars) < 3:
            human_factors += 1

        # Demon will factors
        demon_factors: int = 0
        hawks = [c for c in world.get_characters_at("demon")
                 if "hawk" in c.narrative_tags or "demon_hawk" in c.narrative_tags]
        if len(hawks) >= 1:
            demon_factors += 1

        # Population pressure (demons with high population)
        demon_count = len(world.get_characters_at("demon"))
        if demon_count >= 2:
            demon_factors += 1

        # War debate momentum
        debate_momentum = world.narrative_threads.get("demon_war_debate", 0.0)
        if debate_momentum > 2.0:
            demon_factors += 1

        return human_factors >= 2 and demon_factors >= 2

    @staticmethod
    def _start_war(world: WorldState) -> list[str]:
        """War triggers! Initialize war state."""
        world.war_active = True
        world.war_phase = "preparation"
        world.war_tick_start = world.tick_count
        world.war_side_advantage = "demon"  # demons start with advantage (surprise attack)

        return [
            "[战争议会] 魔族将军戈尔姆的声音响彻议会：'时机已到——全军出击！'",
            "[战争议会] 投票结果: 激进派以微弱优势胜出。魔族军队开始向边境集结。",
            "[深渊边缘] 魔力涌动——魔族战争的号角声在深渊中回荡。",
        ]

    @staticmethod
    def _progress_war(world: WorldState) -> list[str]:
        """Progress the war through phases."""
        ticks_in_phase = world.tick_count - world.war_tick_start
        events: list[str] = []

        if world.war_phase == "preparation" and ticks_in_phase > 30:
            world.war_phase = "skirmish"
            world.war_tick_start = world.tick_count
            events = [
                "[城墙] 魔族先锋部队出现在铁门关外——边境冲突正式开始。",
                "[军营] 将军哈尔紧急部署防线，士兵们握紧了武器。",
                "[指挥部] 急报已经发往王座厅——请求增援。",
            ]

        elif world.war_phase == "skirmish" and ticks_in_phase > 60:
            world.war_phase = "battle"
            world.war_tick_start = world.tick_count
            events = [
                "[城墙] 魔族主力部队抵达——全面会战一触即发。",
                "[军营] 哈尔将军站在城墙上，望着黑压压的魔族大军：'今日，不退。'",
                "[伤兵营] 第一批伤兵被抬了进来——战争已经不再是纸上谈兵。",
            ]

        elif world.war_phase == "battle" and ticks_in_phase > 90:
            # War resolution — weighted random
            outcome = random.choices(
                ["human_victory", "demon_victory", "stalemate"],
                weights=[30, 40, 30],
            )[0]
            world.war_phase = outcome
            world.war_active = False
            events = [
                f"[城墙] 会战结束——{WarSystem._outcome_text(outcome)}",
            ]
            if outcome == "human_victory":
                world.war_side_advantage = "human"

        elif world.war_phase in ("preparation", "skirmish", "battle"):
            # Generate minor war events between phase transitions
            if random.random() < 0.3:
                events += WarSystem._war_minor_events(world)

        return events

    @staticmethod
    def _war_minor_events(world: WorldState) -> list[str]:
        events: list[str] = []
        phase = world.war_phase
        sub = random.choice(["城墙", "军营", "伤兵营", "指挥部"])
        chars = world.get_characters_at("front")
        ch_name = random.choice(chars).name if chars else "士兵们"

        if phase == "preparation":
            pool = [
                f"[{sub}] {ch_name}紧张地检查着武器装备。",
                f"[{sub}] 远处的烟尘越来越近了——每个人都知道这意味着什么。",
                f"[{sub}] 补给车队抵达，带来了箭矢和药品。",
            ]
        elif phase == "skirmish":
            pool = [
                f"[{sub}] {ch_name}在最近一次交火中受了轻伤，但拒绝离开前线。",
                f"[{sub}] 魔族的一支突击队被击退——但这只是试探。",
                f"[{sub}] 战报：边境防线暂时守住，但压力在增大。",
            ]
        else:
            pool = [
                f"[{sub}] {ch_name}在混战中倒下——被拖往伤兵营。",
                f"[{sub}] 魔族的攻势一波接一波，城墙在颤抖。",
                f"[{sub}] 哈尔将军亲自上阵——这可能是最后的防线。",
            ]
        events.append(random.choice(pool))
        return events

    @staticmethod
    def _outcome_text(outcome: str) -> str:
        if outcome == "human_victory":
            return "人类军队守住了铁门关。魔族暂时撤退，但威胁并未解除。"
        elif outcome == "demon_victory":
            return "魔族突破了防线。铁门关陷落，人类王国陷入了前所未有的危机。"
        return "双方伤亡惨重，战线陷入了僵持。没有赢家，只有更多的伤兵。"


def is_wartime(world: WorldState) -> bool:
    return world.war_active
