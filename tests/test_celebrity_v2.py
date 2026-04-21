"""Celebrity v2 (2026-04-21) 변경사항 회귀 테스트.

1. Scene.image_query 필드 라운드트립
2. 유명인 프롬프트에서 '출처: 나무위키' 강제 규칙 제거 확인
3. 프롬프트에 스토리텔링 톤 + per-scene image_query 지시가 포함됨을 확인
"""
from __future__ import annotations

from datetime import datetime

import pytest

from src.analyzer.celebrity_prompt import (
    CELEBRITY_ANALYZE_PROMPT,
    build_celebrity_prompt,
)
from src.analyzer.script_models import Scene
from src.scraper.celebrity_models import CelebrityInfo


# --- Scene.image_query 라운드트립 ---------------------------------------


class TestSceneImageQuery:
    def _make(self, image_query: str | None = None) -> Scene:
        return Scene(
            id=3, timestamp=6.0, duration=4.0, type="body",
            text="서울대를\n졸업했어요", voice_text="서울대를 졸업했어요",
            emphasis="medium", highlight_words=("서울대",),
            image_query=image_query,
        )

    def test_default_is_none(self):
        assert self._make().image_query is None

    def test_accepts_value(self):
        s = self._make("서울대학교 정문")
        assert s.image_query == "서울대학교 정문"

    def test_to_dict_omits_when_none(self):
        d = self._make(None).to_dict()
        assert "image_query" not in d

    def test_to_dict_includes_when_set(self):
        d = self._make("서울대학교 정문").to_dict()
        assert d["image_query"] == "서울대학교 정문"

    def test_from_dict_roundtrip(self):
        original = self._make("서울대학교 정문")
        restored = Scene.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_legacy_no_field(self):
        """기존 JSON(image_query 필드 없음)도 None으로 파싱."""
        legacy = {
            "id": 1, "timestamp": 0.0, "duration": 3.0, "type": "title",
            "text": "제목", "voice_text": "제목", "emphasis": "high",
        }
        scene = Scene.from_dict(legacy)
        assert scene.image_query is None

    def test_from_dict_camel_case(self):
        d = {
            "id": 1, "timestamp": 0.0, "duration": 3.0, "type": "title",
            "text": "t", "voice_text": "t", "emphasis": "high",
            "imageQuery": "국회 본회의장",
        }
        scene = Scene.from_dict(d)
        assert scene.image_query == "국회 본회의장"


# --- 프롬프트 변경 ------------------------------------------------------


class TestCelebrityPromptV2:
    def _info(self) -> CelebrityInfo:
        return CelebrityInfo(
            name="테스트인물",
            summary="테스트 요약",
            source_url="https://namu.wiki/w/test",
            birth_date="1970년",
            profession="정치인",
            career_highlights=("서울대학교 졸업", "국회의원 당선"),
            trivia=("재미있는 일화",),
        )

    def test_no_namuwiki_attribution_rule(self):
        """마지막 씬에 '출처: 나무위키'를 강제하는 규칙이 제거됐는지."""
        prompt = build_celebrity_prompt(self._info())
        # v1의 강제 규칙 문구가 사라졌는지
        assert "마지막 씬의 text는 반드시" not in prompt
        # 반대로 "출처 문구는 쓰지 마세요" 지침이 있어야 함
        assert "출처" in prompt  # 일반 언급은 허용 (context·description)
        assert "쓰지 마세요" in prompt or "표기 X" in prompt

    def test_storytelling_tone_instructions(self):
        prompt = build_celebrity_prompt(self._info())
        assert "친구" in prompt or "이야기" in prompt
        assert "스토리" in prompt or "훅" in prompt

    def test_image_query_field_instruction(self):
        prompt = build_celebrity_prompt(self._info())
        assert "image_query" in prompt
        # 예시로 서울대학교·국회의사당 같은 구체적 키워드 예시가 들어 있어야
        assert "서울대" in prompt or "국회" in prompt

    def test_renders_with_actual_info(self):
        prompt = build_celebrity_prompt(self._info())
        assert "테스트인물" in prompt
        assert "서울대학교 졸업" in prompt
        assert "국회의원 당선" in prompt
        assert "재미있는 일화" in prompt
