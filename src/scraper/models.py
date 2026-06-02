"""BlindPost and Comment data models.

Frozen dataclasses ensure immutability (Constitution Principle VI).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta


KST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class Comment:
    """A single comment on a Blind post."""
    text: str
    likes: int = 0
    author: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Comment:
        return cls(
            text=data["text"],
            likes=data.get("likes", 0),
            author=data.get("author", ""),
        )


@dataclass(frozen=True)
class BlindPost:
    """A Blind community post with comments."""
    title: str
    author: str
    body: str
    comments: tuple[Comment, ...] = field(default_factory=tuple)
    url: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "body": self.body,
            "comments": [c.to_dict() for c in self.comments],
            "url": self.url,
            "created_at": self.created_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> BlindPost:
        comments = tuple(
            Comment.from_dict(c) for c in data.get("comments", [])
        )
        created_at = data.get("created_at", "")
        if not created_at:
            created_at = datetime.now(KST).isoformat()

        return cls(
            title=data["title"],
            author=data.get("author", ""),
            body=data["body"],
            comments=comments,
            url=data.get("url", ""),
            created_at=created_at,
        )

    @classmethod
    def from_json(cls, json_str: str) -> BlindPost:
        data = json.loads(json_str)
        return cls.from_dict(data)
