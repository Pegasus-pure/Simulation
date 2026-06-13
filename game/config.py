## Runtime configuration — API keys, user preferences.
## Never commit config.json; it's in .gitignore.
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict


CONFIG_PATH: str = os.path.join(os.path.dirname(__file__), "..", "config.json")


@dataclass(slots=True)
class Config:
    """Singleton config loaded from config.json."""
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    api_model: str = "gpt-4o-mini"
    ai_enabled: bool = False
    enable_real_time_events: bool = True
    tick_interval_ms: int = 3000  # ms between ticks

    @staticmethod
    def load() -> Config:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
        return Config()

    def save(self) -> None:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    def set_api(self, key: str, base: str = "", model: str = "") -> None:
        self.api_key = key.strip()
        if base:
            self.api_base = base.strip()
        if model:
            self.api_model = model.strip()
        self.ai_enabled = bool(self.api_key)
        self.save()
