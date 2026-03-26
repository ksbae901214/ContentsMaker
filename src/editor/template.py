"""Template management — reusable style presets.

All functions return new objects without mutating the input.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT

TEMPLATES_DIR = PROJECT_ROOT / "data" / "templates"


@dataclass(frozen=True)
class Template:
    name: str
    subtitle_style: dict
    transition: dict
    voice: str
    bgm_enabled: bool

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "subtitle_style": self.subtitle_style,
            "transition": self.transition,
            "voice": self.voice,
            "bgm_enabled": self.bgm_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Template:
        return cls(
            name=data["name"],
            subtitle_style=data.get("subtitle_style", {}),
            transition=data.get("transition", {}),
            voice=data.get("voice", "ko-KR-SunHiNeural"),
            bgm_enabled=data.get("bgm_enabled", True),
        )


def save_template(template: Template) -> Path:
    """Save template to data/templates/{name}.json."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(
        c for c in template.name[:30] if c.isalnum() or c in " _-"
    ).strip().replace(" ", "_") or "untitled"

    path = TEMPLATES_DIR / f"{safe_name}.json"
    path.write_text(
        json.dumps(template.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_templates() -> list[Template]:
    """Load all templates from data/templates/."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            templates.append(Template.from_dict(data))
        except (json.JSONDecodeError, KeyError):
            continue
    return templates
