## Academy system — student growth, assessments, graduation, new intake.
## Operates on the WorldState each tick, modifying character attributes.
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world_state import WorldState
    from game.character import Character

# ── Constants ──────────────────────────────────────────────────────

STUDENT_NAMES_POOL: list[tuple[str, str, str]] = [
    ("格伦", "male", "commoner"), ("莉娜", "female", "noble"),
    ("雷恩", "male", "warrior"), ("索菲亚", "female", "scholar"),
    ("达里安", "male", "noble"), ("菲奥娜", "female", "commoner"),
]
GRADUATION_COMBAT_THRESHOLD: int = 55
GRADUATION_MAGIC_THRESHOLD: int = 55
MAX_STUDENTS: int = 8
ASSESSMENT_INTERVAL_TICKS: int = 20  # roughly every simulated 20 min (~1 real minute at 3s ticks)


class AcademySystem:
    """Manages student lifecycle: growth, monthly assessments, graduation, intake."""

    @staticmethod
    def tick(world: WorldState) -> list[str]:
        """Run one tick of academy logic. Returns event texts to inject."""
        events: list[str] = []
        students = [c for c in world.characters.values()
                    if c.location == "academy" and c.status == "alive" and c.role == "学生"]

        # ── Growth: small random attribute bumps ──
        for ch in students:
            attr = random.choice(["combat", "magic", "tactics", "wisdom", "will"])
            delta = random.randint(0, 2)
            current = getattr(ch, attr)
            setattr(ch, attr, min(100, current + delta))

        # ── Assessment check ──
        if world.tick_count % ASSESSMENT_INTERVAL_TICKS == 0:
            events += AcademySystem._run_assessment(world, students)

        # ── Graduation check ──
        events += AcademySystem._check_graduation(world, students)

        # ── Intake: fill empty slots ──
        events += AcademySystem._check_intake(world, students)

        return events

    @staticmethod
    def _run_assessment(world: WorldState, students: list[Character]) -> list[str]:
        events: list[str] = []
        sub = random.choice(["训练场", "讲堂"])

        for ch in students:
            score = random.randint(0, 100)
            primary = max(ch.combat, ch.magic)
            if score >= 70:
                # Pass with distinction
                attr = random.choice(["combat", "magic"])
                delta = random.randint(3, 8)
                setattr(ch, attr, min(100, getattr(ch, attr) + delta))
                events.append(
                    f"[{sub}] 月度考核：{ch.name}表现优异，{attr}提升了{delta}点。"
                )
            elif score >= 40:
                events.append(
                    f"[{sub}] 月度考核：{ch.name}通过了考核，表现中规中矩。"
                )
            else:
                events.append(
                    f"[{sub}] 月度考核：{ch.name}成绩不佳，需要加倍努力。"
                )
                ch.narrative_tags.append("struggling")
        return events

    @staticmethod
    def _check_graduation(world: WorldState, students: list[Character]) -> list[str]:
        events: list[str] = []
        for ch in students:
            if ch.age >= 18 and (ch.combat >= GRADUATION_COMBAT_THRESHOLD
                                 or ch.magic >= GRADUATION_MAGIC_THRESHOLD):
                ch.status = "graduated"
                ch.location = "front"
                ch.role = "毕业生"
                events.append(
                    f"[院长室] {ch.name}通过了最终考核，正式从学院毕业，被派往前线报到。"
                )
                ch.narrative_tags = []
        return events

    @staticmethod
    def _check_intake(world: WorldState, students: list[Character]) -> list[str]:
        events: list[str] = []
        active = [c for c in students if c.status == "alive"]
        if len(active) >= MAX_STUDENTS:
            return events

        # Only intake occasionally
        if random.random() > 0.05:
            return events

        name, gender, origin = random.choice(STUDENT_NAMES_POOL)
        new_id = f"student_{world.tick_count}"
        from game.character import Character
        ch = Character(
            id=new_id, name=name, race="human", gender=gender,
            age=16, origin=origin, location="academy",
            combat=random.randint(20, 45), magic=random.randint(20, 45),
            tactics=random.randint(15, 30), wisdom=random.randint(15, 35),
            will=random.randint(30, 60), social=random.randint(25, 55),
            role="学生", faction="academy",
        )
        world.characters[new_id] = ch
        events.append(
            f"[院长室] 新生{name}入学——皇家勇者学院迎来了新的血液。"
        )
        return events

    @staticmethod
    def accelerate_for_war(world: WorldState) -> list[str]:
        """Called when war breaks out — accelerate training, early graduation."""
        events: list[str] = []
        students = [c for c in world.characters.values()
                    if c.location == "academy" and c.status == "alive" and c.role == "学生"]

        for ch in students:
            ch.combat = min(100, ch.combat + random.randint(2, 5))
            ch.will = min(100, ch.will + random.randint(1, 3))

        events.append(
            "[院长室] 战争爆发！院长宣布加速训练计划——所有学生进入实战准备。"
        )
        if students:
            names = "、".join(c.name for c in students[:4])
            events.append(
                f"[训练场] {names}的训练强度翻倍——前线的炮火声似乎已经能听见了。"
            )
        return events
