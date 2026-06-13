## Character data model — typed, serialisable, GC-free.
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Character:
    """A living entity in the simulated world."""
    id: str
    name: str            # display name in "en (zh)" format
    race: str            # "human" | "demon"
    gender: str          # "male" | "female"
    age: int             # simulated years
    origin: str          # "noble" | "commoner" | "warrior" | "scholar" | "demon"
    location: str        # current location ID

    # Core attributes [0-100]
    combat: int = 50
    magic: int = 50
    tactics: int = 50
    wisdom: int = 50
    will: int = 50
    social: int = 50

    # Role
    role: str = ""       # "king", "student", "general", "advisor", "demon_lord", etc.
    faction: str = ""    # "human_kingdom" | "demon_tribe" | "academy" | "neutral"
    status: str = "alive"  # "alive" | "dead" | "missing"
    name_zh: str = ""    # Chinese name
    name_en: str = ""    # English name

    # Relationships: {target_id: relation_value}
    # 0 = mortal enemy, 100 = soulmate
    relations: dict[str, int] = field(default_factory=dict)

    # Narrative tags for the state machine
    narrative_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "name_zh": self.name_zh, "name_en": self.name_en, "race": self.race,
            "gender": self.gender, "age": self.age, "origin": self.origin,
            "location": self.location, "combat": self.combat, "magic": self.magic,
            "tactics": self.tactics, "wisdom": self.wisdom, "will": self.will,
            "social": self.social, "role": self.role, "faction": self.faction,
            "status": self.status, "relations": dict(self.relations),
            "narrative_tags": list(self.narrative_tags),
        }

    @staticmethod
    def from_dict(d: dict) -> Character:
        name_zh = d.get("name_zh", d.get("name", ""))
        name_en = d.get("name_en", "")
        display_name = f"{name_en} ({name_zh})" if name_en else name_zh
        return Character(
            id=d["id"], name=display_name, name_zh=name_zh, name_en=name_en, race=d["race"],
            gender=d.get("gender", "male"), age=d.get("age", 20),
            origin=d.get("origin", "commoner"), location=d.get("location", "academy"),
            combat=d.get("combat", 50), magic=d.get("magic", 50),
            tactics=d.get("tactics", 50), wisdom=d.get("wisdom", 50),
            will=d.get("will", 50), social=d.get("social", 50),
            role=d.get("role", ""), faction=d.get("faction", ""),
            status=d.get("status", "alive"),
            relations=d.get("relations", {}),
            narrative_tags=d.get("narrative_tags", []),
        )
