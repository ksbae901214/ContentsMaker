"""Project management — save and load editing state.

All functions return new objects without mutating the input.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.config.settings import PROJECT_ROOT

PROJECTS_DIR = PROJECT_ROOT / "data" / "projects"


class ProjectError(Exception):
    """Raised when a project operation fails."""


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    created_at: str
    updated_at: str
    script_path: str
    image_paths: dict[int, str] = field(default_factory=dict)
    video_paths: dict[int, str] = field(default_factory=dict)
    audio_path: str | None = None
    output_path: str | None = None
    template_name: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "script_path": self.script_path,
            "image_paths": {str(k): v for k, v in self.image_paths.items()},
            "video_paths": {str(k): v for k, v in self.video_paths.items()},
            "audio_path": self.audio_path,
            "output_path": self.output_path,
            "template_name": self.template_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Project:
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            script_path=data["script_path"],
            image_paths={int(k): v for k, v in data.get("image_paths", {}).items()},
            video_paths={int(k): v for k, v in data.get("video_paths", {}).items()},
            audio_path=data.get("audio_path"),
            output_path=data.get("output_path"),
            template_name=data.get("template_name"),
        )


def save_project(
    name: str,
    script_path: str,
    image_paths: dict[int, str] | None = None,
    audio_path: str | None = None,
    output_path: str | None = None,
    project_id: str | None = None,
) -> Project:
    """Save a project to data/projects/{id}.json."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat()
    pid = project_id or str(uuid4())[:8]

    project = Project(
        id=pid,
        name=name,
        created_at=now,
        updated_at=now,
        script_path=script_path,
        image_paths=image_paths or {},
        audio_path=audio_path,
        output_path=output_path,
    )

    project_path = PROJECTS_DIR / f"{pid}.json"

    # If updating existing project, preserve created_at
    if project_path.exists():
        existing = json.loads(project_path.read_text(encoding="utf-8"))
        project = Project(
            id=pid,
            name=name,
            created_at=existing.get("created_at", now),
            updated_at=now,
            script_path=script_path,
            image_paths=image_paths or {},
            audio_path=audio_path,
            output_path=output_path,
        )

    project_path.write_text(
        json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return project


def load_project(project_id: str) -> Project:
    """Load a project from data/projects/{id}.json."""
    project_path = PROJECTS_DIR / f"{project_id}.json"
    if not project_path.exists():
        raise ProjectError(f"프로젝트를 찾을 수 없습니다: {project_id}")

    data = json.loads(project_path.read_text(encoding="utf-8"))
    return Project.from_dict(data)


def list_projects() -> list[dict]:
    """List all saved projects, sorted by updated_at descending."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    projects = []
    for f in PROJECTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            projects.append({
                "id": data["id"],
                "name": data["name"],
                "updated_at": data["updated_at"],
                "created_at": data.get("created_at", ""),
                "has_output": bool(data.get("output_path")),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(projects, key=lambda p: p["updated_at"], reverse=True)


def delete_project(project_id: str) -> bool:
    """Delete a project file."""
    project_path = PROJECTS_DIR / f"{project_id}.json"
    if project_path.exists():
        project_path.unlink()
        return True
    return False
