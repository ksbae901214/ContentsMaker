"""Tests for Scene.clip_query field (Phase 9 YouTube source).

TDD RED phase: clip_query serialization roundtrip.
"""
from __future__ import annotations

from src.analyzer.script_models import Scene


def _base_scene(**kwargs) -> Scene:
    defaults = dict(
        id=1,
        timestamp=0.0,
        duration=4.0,
        type="body",
        text="텍스트",
        voice_text="보이스",
    )
    defaults.update(kwargs)
    return Scene(**defaults)


class TestSceneClipQuery:
    def test_serialized_when_set(self):
        """clip_query is included in to_dict() when set."""
        scene = _base_scene(clip_query="손흥민 골 장면")
        d = scene.to_dict()
        assert d["clip_query"] == "손흥민 골 장면"

    def test_omitted_when_none(self):
        """clip_query is NOT included in to_dict() when None."""
        scene = _base_scene(clip_query=None)
        d = scene.to_dict()
        assert "clip_query" not in d

    def test_roundtrip(self):
        """Serialize then deserialize preserves clip_query value."""
        scene = _base_scene(clip_query="손흥민 챔피언스리그")
        d = scene.to_dict()
        restored = Scene.from_dict(d)
        assert restored.clip_query == "손흥민 챔피언스리그"

    def test_camel_case_from_dict(self):
        """clipQuery (camelCase) is recognized in from_dict."""
        d = {
            "id": 1,
            "timestamp": 0.0,
            "duration": 4.0,
            "type": "body",
            "text": "텍스트",
            "voice_text": "보이스",
            "clipQuery": "손흥민 인터뷰",
        }
        scene = Scene.from_dict(d)
        assert scene.clip_query == "손흥민 인터뷰"

    def test_none_when_missing(self):
        """clip_query defaults to None when absent from dict."""
        d = {
            "id": 1,
            "timestamp": 0.0,
            "duration": 4.0,
            "type": "body",
            "text": "텍스트",
            "voice_text": "보이스",
        }
        scene = Scene.from_dict(d)
        assert scene.clip_query is None

    def test_empty_string_coerced_to_none(self):
        """Empty string clip_query is coerced to None on deserialization."""
        d = {
            "id": 1,
            "timestamp": 0.0,
            "duration": 4.0,
            "type": "body",
            "text": "텍스트",
            "voice_text": "보이스",
            "clip_query": "",
        }
        scene = Scene.from_dict(d)
        assert scene.clip_query is None
