"""정보쇼츠 V1.0 렌더 CLI — config 검증·프롬프트·스크립트·props 조립 테스트 (045)."""
from __future__ import annotations

import copy

import pytest

from scripts.render_info_v1 import (
    FORMAT,
    build_props,
    build_script,
    chat_block,
    config_warnings,
    image_path,
    image_prompt,
    missing_images,
    validate_config,
    work_dir,
)


def _cfg(**over) -> dict:
    chapters = [
        {"image_prompt": "a lone orangutan mother", "sentences": ["오랑우탄 엄마는 8년을 혼자 키웁니다."]},
    ] + [
        {"image_prompt": f"scene {i}", "sentences": [f"{i}장 첫 문장입니다.", f"{i}장 두 번째 문장입니다."]}
        for i in range(1, 8)
    ]
    cfg = {
        "format": FORMAT,
        "slug": "orangutan_mother",
        "title": "오랑우탄 엄마는 새끼의",
        "watermark": "made by 정보쇼츠",
        "topic_type": "paper",
        "fact_sources": [{"label": "PNAS 2026", "url": "https://www.pnas.org/doi/10.1073/x"}],
        "caption": "오랑우탄 엄마는 새끼의\n\n출처 : PNAS, 2026",
        "chapters": chapters,
    }
    cfg.update(over)
    return cfg


# ── 검증 (차단) ──────────────────────────────────────────────────
def test_valid_config_passes():
    validate_config(_cfg())


def test_wrong_format_blocked():
    with pytest.raises(ValueError, match="format"):
        validate_config(_cfg(format="news_v4"))


@pytest.mark.parametrize("slug", ["", "Bad Slug", "../x"])
def test_bad_slug_blocked(slug):
    with pytest.raises(ValueError, match="slug"):
        validate_config(_cfg(slug=slug))


def test_too_few_chapters_blocked():
    cfg = _cfg()
    with pytest.raises(ValueError, match="챕터"):
        validate_config({**cfg, "chapters": cfg["chapters"][:2]})


def test_chapter_without_sentences_blocked():
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    chapters[3]["sentences"] = []
    with pytest.raises(ValueError, match="문장"):
        validate_config({**cfg, "chapters": chapters})


def test_chapter_without_prompt_or_image_blocked():
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    del chapters[2]["image_prompt"]
    with pytest.raises(ValueError, match="image_prompt"):
        validate_config({**cfg, "chapters": chapters})


def test_paper_type_requires_fact_sources():
    with pytest.raises(ValueError, match="fact_sources"):
        validate_config(_cfg(fact_sources=[]))


def test_story_type_does_not_require_fact_sources():
    validate_config(_cfg(topic_type="story", fact_sources=[]))


def test_namuwiki_source_blocked():
    with pytest.raises(ValueError, match="나무위키"):
        validate_config(_cfg(fact_sources=[{"label": "x", "url": "https://namu.wiki/w/x"}]))


def test_over_length_blocked():
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    chapters[1]["sentences"] = ["가" * 1600]
    with pytest.raises(ValueError, match="상한"):
        validate_config({**cfg, "chapters": chapters})


# ── 경고 ────────────────────────────────────────────────────────
def test_cta_words_warned():
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    chapters[-1]["sentences"] = ["팔로우하고 다음 편도 보세요."]
    warns = config_warnings({**cfg, "chapters": chapters})
    assert any("CTA" in w for w in warns)


def test_question_hook_warned():
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    chapters[0]["sentences"] = ["오랑우탄 엄마 아시나요?"]
    assert any("훅" in w for w in config_warnings({**cfg, "chapters": chapters}))


def test_chapter_count_outside_benchmark_warned():
    cfg = _cfg()
    assert any("챕터" in w for w in config_warnings({**cfg, "chapters": cfg["chapters"][:5]}))


# ── 경로·프롬프트 ────────────────────────────────────────────────
def test_image_path_default_and_override():
    cfg = _cfg()
    assert image_path(cfg, 3) == work_dir(cfg) / "images" / "chapter_03.png"
    chapters = copy.deepcopy(cfg["chapters"])
    chapters[3]["image"] = "/tmp/x.png"
    assert str(image_path({**cfg, "chapters": chapters}, 3)) == "/tmp/x.png"


def test_missing_images_lists_absent_chapters(tmp_path):
    cfg = _cfg()
    chapters = copy.deepcopy(cfg["chapters"])
    present = tmp_path / "a.png"
    present.write_bytes(b"x")
    chapters[0]["image"] = str(present)
    missing = missing_images({**cfg, "chapters": chapters})
    assert 0 not in missing and 1 in missing


def test_image_prompt_wraps_style_and_forbids_text():
    cfg = _cfg()
    cover = image_prompt(cfg, 0)
    scene = image_prompt(cfg, 3)
    assert "a lone orangutan mother" in cover and "isolated" in cover
    assert "scene 3" in scene and "engraving" in scene
    assert "No text" in scene


# ── 스크립트·props ───────────────────────────────────────────────
def test_build_script_one_scene_per_sentence():
    script = build_script(_cfg())
    assert len(script.scenes) == 1 + 7 * 2
    assert script.metadata.source_type == FORMAT
    assert script.scenes[1].voice_text == "1장 첫 문장입니다."


def test_build_props_slots_captions_and_title():
    cfg = _cfg()
    n = 1 + 7 * 2
    timings = [{"scene_id": i, "start_ms": i * 2000, "end_ms": i * 2000 + 1800} for i in range(n)]
    props = build_props(cfg, timings)
    assert len(props["images"]) == 8
    assert props["images"][0]["zoomStartMs"] is None
    assert props["images"][1]["zoomStartMs"] is not None
    assert props["durationMs"] == timings[-1]["end_ms"]
    assert props["captions"][0]["startMs"] == 0
    assert props["titleLines"] == ["오랑우탄 엄마는", "새끼의"] or props["titleLines"] == ["오랑우탄 엄마는 새끼의"]
    assert props["watermark"] == "made by 정보쇼츠"


def test_chat_block_has_three_platform_sections_with_sources():
    cfg = _cfg(yt_title="오랑우탄 엄마가 8년 동안 하는 일", description="육아 기간이 가장 긴 유인원 이야기.",
               hashtags=["#오랑우탄", "#동물"])
    block = chat_block(cfg)
    yt, ig, tt = (block.index(h) for h in ("[유튜브]", "[인스타그램]", "[틱톡]"))
    assert yt < ig < tt
    assert "오랑우탄 엄마가 8년 동안 하는 일" in block[yt:ig]
    assert "출처 : PNAS 2026" in block[yt:ig]
    assert "육아 기간이 가장 긴 유인원 이야기." in block[ig:tt]
    assert "#오랑우탄 #동물" in block[tt:]


def test_chat_block_falls_back_to_title_and_caption():
    block = chat_block(_cfg())
    assert block.count("오랑우탄 엄마는 새끼의") >= 2


def test_long_yt_title_and_bad_hashtag_warned():
    warns = config_warnings(_cfg(yt_title="가" * 101, hashtags=["오랑우탄"]))
    assert any("yt_title" in w for w in warns)
    assert any("해시태그" in w for w in warns)


def test_default_watermark_is_channel_name():
    cfg = _cfg()
    del cfg["watermark"]
    n = 1 + 7 * 2
    timings = [{"scene_id": i, "start_ms": i * 2000, "end_ms": i * 2000 + 1800} for i in range(n)]
    assert build_props(cfg, timings)["watermark"] == "made by 호기심 도감"


def test_image_mood_is_added_to_every_prompt():
    cfg = _cfg(image_mood="adorable chubby round-faced character")
    assert "adorable chubby round-faced character" in image_prompt(cfg, 0)
    assert "adorable chubby round-faced character" in image_prompt(cfg, 4)


def test_no_image_mood_keeps_prompt_unchanged():
    assert "None" not in image_prompt(_cfg(), 2)
    assert "  " not in image_prompt(_cfg(), 2)
