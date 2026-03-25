"""Shared test fixtures for ContentsMaker."""
import json
import pytest
from pathlib import Path

from src.analyzer.script_models import (
    ShortsScript, Metadata, Scene, AudioConfig, BackgroundConfig,
)
from src.scraper.models import BlindPost, Comment


@pytest.fixture
def sample_scene_title():
    return Scene(
        id=1, timestamp=0.0, duration=5.0, type="title",
        text="언니 결혼식에\n안 오겠다는 남자친구",
        voice_text="언니 결혼식에 안 오겠다는 남자친구",
        emphasis="high",
    )


@pytest.fixture
def sample_scene_body():
    return Scene(
        id=2, timestamp=5.0, duration=8.0, type="body",
        text="친언니 결혼식에\n남자친구한테\n인사 겸 오라고 했거든요",
        voice_text="친언니가 이번 주 토요일에 결혼식을 하는데 남자친구한테 인사 겸 오라고 했어요.",
        emphasis="medium",
        highlight_words=("결혼식", "남자친구"),
    )


@pytest.fixture
def sample_scene_comment():
    return Scene(
        id=3, timestamp=13.0, duration=6.0, type="comment",
        text="그건 좀\n심하네요",
        voice_text="그건 좀 심하네요.",
        emphasis="low",
    )


@pytest.fixture
def sample_scenes(sample_scene_title, sample_scene_body, sample_scene_comment):
    return (sample_scene_title, sample_scene_body, sample_scene_comment)


@pytest.fixture
def sample_script(sample_scenes):
    return ShortsScript(
        metadata=Metadata(
            title="언니 결혼식에 안 오겠다는 남자친구",
            emotion_type="relatable",
            duration=45.0,
            source_url="",
        ),
        scenes=sample_scenes,
        audio=AudioConfig(
            tts_script="언니 결혼식에 안 오겠다는 남자친구. 친언니가 이번 주 토요일에 결혼식을 하는데. 그건 좀 심하네요.",
            voice="ko-KR-SunHiNeural",
            rate="+20%",
            pitch="+0Hz",
        ),
        background=BackgroundConfig(
            type="gradient",
            colors=("#4169E1", "#1E90FF", "#87CEEB"),
        ),
    )


@pytest.fixture
def sample_post():
    return BlindPost(
        title="언니 결혼식에 안 오겠다는 남자친구",
        author="IT/개발 · 어쩌라고",
        body="친언니가 이번 주 토요일에 결혼식을 하는데 결혼 예정인 남자친구한테 인사 겸 오라고 했거든요. 근데 걔가 싫다고 안 간다는 거예요.",
        comments=(
            Comment(text="그건 좀 심하네요", likes=42, author="익명"),
            Comment(text="레드플래그 아닌가요", likes=15, author="익명"),
        ),
        url="",
    )


@pytest.fixture
def sample_script_dict():
    return {
        "metadata": {
            "title": "테스트 제목",
            "emotion_type": "funny",
            "duration": 45.0,
        },
        "scenes": [
            {"id": 1, "timestamp": 0, "duration": 5, "type": "title",
             "text": "제목 텍스트", "voice_text": "제목 텍스트입니다"},
            {"id": 2, "timestamp": 5, "duration": 8, "type": "body",
             "text": "본문 텍스트", "voice_text": "본문 내용입니다"},
        ],
        "audio": {"tts_script": "제목 텍스트입니다 본문 내용입니다", "voice": "", "rate": "", "pitch": ""},
        "background": {"type": "gradient", "colors": []},
    }


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Temporary data directory mimicking project structure."""
    for d in ["scripts", "audio", "images", "outputs", "raw", "bgm"]:
        (tmp_path / d).mkdir()
    return tmp_path
