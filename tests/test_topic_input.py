"""Tests for TopicInput model (T006).

TDD RED phase: these tests define the expected behavior of TopicInput
before implementation exists.
"""
import json
from datetime import datetime, timezone, timedelta

import pytest

from src.scraper.topic_input import TopicInput, save_topic, TopicInputError


KST = timezone(timedelta(hours=9))


class TestCreateTopicInput:
    def test_create_topic_input(self):
        topic_input = TopicInput(
            topic="즐겨 먹던 과자들의 배신",
            style="narration",
            tone="재밌게",
            details="90년대 과자 중심으로",
        )
        assert topic_input.topic == "즐겨 먹던 과자들의 배신"
        assert topic_input.style == "narration"
        assert topic_input.tone == "재밌게"
        assert topic_input.details == "90년대 과자 중심으로"

    def test_default_style(self):
        topic_input = TopicInput(topic="테스트 주제입니다")
        assert topic_input.style == "narration"

    def test_frozen(self):
        topic_input = TopicInput(topic="테스트 주제입니다")
        with pytest.raises(AttributeError):
            topic_input.topic = "변경 시도"


class TestValidation:
    def test_validation_min_length(self):
        with pytest.raises(TopicInputError):
            TopicInput(topic="짧은")

    def test_validation_invalid_style(self):
        with pytest.raises(TopicInputError):
            TopicInput(topic="유효한 주제입니다", style="invalid_style")


class TestSerialization:
    def test_to_dict_roundtrip(self):
        original = TopicInput(
            topic="즐겨 먹던 과자들의 배신",
            style="narration",
            tone="재밌게",
            details="90년대 과자 중심으로",
        )
        data = original.to_dict()
        restored = TopicInput.from_dict(data)
        assert restored.topic == original.topic
        assert restored.style == original.style
        assert restored.tone == original.tone
        assert restored.details == original.details

    def test_created_at_auto(self):
        topic_input = TopicInput(topic="자동 시간 테스트 주제")
        assert topic_input.created_at is not None
        parsed = datetime.fromisoformat(topic_input.created_at)
        assert parsed.tzinfo is not None
        now_kst = datetime.now(KST)
        diff = abs((now_kst - parsed).total_seconds())
        assert diff < 5


class TestSaveTopic:
    def test_save_topic(self, tmp_path):
        topic_input = TopicInput(
            topic="즐겨 먹던 과자들의 배신",
            style="narration",
            tone="재밌게",
        )
        saved_path = save_topic(topic_input, output_dir=tmp_path)
        assert saved_path.exists()
        assert saved_path.suffix == ".json"

        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert data["topic"] == "즐겨 먹던 과자들의 배신"
        assert data["style"] == "narration"

        restored = TopicInput.from_dict(data)
        assert restored.topic == topic_input.topic
