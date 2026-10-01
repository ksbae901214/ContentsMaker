"""V5.0 증거 삽입형 TTS 논평 — config 게이트·경고·스크립트 구성 (043 Phase B)."""
from __future__ import annotations

import pytest

from scripts.render_evidence_v5 import (
    VOICE_NAME,
    build_script,
    chat_block,
    config_warnings,
    evidence_count,
    source_label,
    validate_config,
    with_scene_text,
)

BASE = {
    "format": "evidence_v5",
    "slug": "t_v5_jang",
    "category": "political",
    "title": "밤새 선거무효 외치더니",
    "yt_title": "밤새 선거무효 외치더니 조용해진 장동혁",
    "yt_title_alt": "이기니까 입 닫은 국민의힘 지도부",
    "hashtags": ["#장동혁", "#선거무효", "#국민의힘"],
    "persons": ["장동혁"],
    "headline": ["밤새 선거무효 외쳤는데", "이기니까 조용?"],
    "fact_sources": [{"title": "연합뉴스", "url": "https://n.news.naver.com/1"}],
    "sources": {
        "a": {"query": "장동혁 선거무효", "channel": "MBC"},
        "b": {"query": "오세훈 당선", "channel": "JTBC"},
    },
    "scenes": [
        {"mode": "clip", "source": "a", "start_sec": 3.0, "duration": 4.0,
         "text": "당연히 선거 무효 사유입니다", "pop": "선거 무효!"},
        {"mode": "tts", "source": "b", "voice": "밤새 선관위 위원장실까지 쳐들어갔던 국민의힘 지도부."},
        {"mode": "tts", "source": "b", "voice": "그런데 새벽 사이 대반전이 일어났습니다.", "flash": True},
    ],
}


def _with(**over) -> dict:
    return {**BASE, **over}


class TestValidate:
    def test_base_passes(self):
        validate_config(BASE)

    def test_wrong_format(self):
        with pytest.raises(ValueError, match="evidence_v5"):
            validate_config(_with(format="v2_2"))

    @pytest.mark.parametrize("key", ["slug", "title", "sources", "scenes"])
    def test_required(self, key):
        with pytest.raises(ValueError, match=key):
            validate_config({k: v for k, v in BASE.items() if k != key})

    def test_bad_mode(self):
        scenes = [{**BASE["scenes"][1], "mode": "photo"}]
        with pytest.raises(ValueError, match="mode"):
            validate_config(_with(scenes=scenes))

    def test_unknown_source(self):
        scenes = [{**BASE["scenes"][1], "source": "zz"}]
        with pytest.raises(ValueError, match="zz"):
            validate_config(_with(scenes=scenes))

    def test_clip_duration_range(self):
        scenes = [{**BASE["scenes"][0], "duration": 15.0}, *BASE["scenes"][1:]]
        with pytest.raises(ValueError, match="duration"):
            validate_config(_with(scenes=scenes))

    def test_clip_needs_text(self):
        clip = {k: v for k, v in BASE["scenes"][0].items() if k != "text"}
        with pytest.raises(ValueError, match="text"):
            validate_config(_with(scenes=[clip, *BASE["scenes"][1:]]))

    def test_tts_needs_voice(self):
        scenes = [*BASE["scenes"][:1], {"mode": "tts", "source": "b", "voice": ""}]
        with pytest.raises(ValueError, match="voice"):
            validate_config(_with(scenes=scenes))

    def test_hook_may_be_tts(self):
        # 상위 10편 중 다수가 TTS 훅으로 시작한다 — V2.2 와 달리 첫 씬 clip 강제 없음
        validate_config(_with(scenes=BASE["scenes"][1:]))

    def test_fact_sources_required(self):
        with pytest.raises(ValueError, match="fact_sources"):
            validate_config({k: v for k, v in BASE.items() if k != "fact_sources"})

    def test_namuwiki_blocked(self):
        with pytest.raises(ValueError, match="나무위키"):
            validate_config(_with(fact_sources=[{"url": "https://namu.wiki/w/x"}]))

    def test_fact_gate_off(self):
        cfg = {k: v for k, v in BASE.items() if k != "fact_sources"}
        validate_config({**cfg, "fact_gate": "off"})

    def test_bad_evidence_marks(self):
        sc = {**BASE["scenes"][1], "evidence": {"image": "e.png", "marks": [
            {"kind": "circle", "x": 0.9, "y": 0.1, "w": 0.3, "h": 0.1}]}}
        with pytest.raises(ValueError, match="이미지 밖"):
            validate_config(_with(scenes=[*BASE["scenes"][:1], sc]))

    def test_bad_framing_blocked(self):
        sc = {**BASE["scenes"][1], "focus_x": 1.5}
        with pytest.raises(ValueError, match="focus_x"):
            validate_config(_with(scenes=[*BASE["scenes"][:1], sc]))

    def test_report_tone_title_blocked(self):
        with pytest.raises(ValueError):
            validate_config(_with(yt_title="장동혁이 선거무효를 주장했다"))


class TestWarnings:
    def test_base_has_no_evidence_or_symmetry_warning(self):
        warns = config_warnings(BASE)
        # 040 대칭(한쪽 진영·기록 대조)만 침묵 — 편성 비중 경고(shorts_balance)는 유지
        assert not any("한쪽 진영" in w or "기록 대조" in w for w in warns)
        assert not any("증거가 없습니다" in w for w in warns)
        assert not any("인트로" in w for w in warns)

    def test_no_evidence_warns(self):
        warns = config_warnings(_with(scenes=BASE["scenes"][1:]))
        assert any("증거가 없습니다" in w for w in warns)

    def test_evidence_card_counts(self):
        sc = {**BASE["scenes"][1], "evidence": {"image": "e.png"}}
        assert evidence_count(_with(scenes=[sc])) == 1
        assert not any("증거가 없습니다" in w for w in config_warnings(_with(scenes=[sc])))

    def test_headline_three_lines_warns(self):
        warns = config_warnings(_with(headline=["a", "b", "c"]))
        assert any("2줄" in w for w in warns)

    def test_headline_long_line_warns(self):
        warns = config_warnings(_with(headline=["가" * 16, "나"]))
        assert any("14자" in w for w in warns)

    def test_alt_title_and_hashtags_warn(self):
        cfg = {k: v for k, v in BASE.items() if k not in ("yt_title_alt", "hashtags")}
        warns = config_warnings(cfg)
        assert any("yt_title_alt" in w for w in warns)
        assert any("hashtags" in w for w in warns)

    def test_short_video_warns(self):
        assert any("60~66초" in w for w in config_warnings(BASE))

    def test_missing_source_credit_warns(self):
        sources = {k: {"query": v["query"]} for k, v in BASE["sources"].items()}
        warns = config_warnings(_with(sources=sources))
        assert any("출처" in w for w in warns)


class TestLabels:
    def test_source_label_from_channels(self):
        assert source_label(BASE) == "영상출처: MBC, JTBC"

    def test_source_label_explicit(self):
        assert source_label(_with(source_label="화면출처: 국회방송")) == "화면출처: 국회방송"

    def test_source_label_ignores_comment_keys(self):
        sources = {**BASE["sources"], "_comment": "설명"}
        assert source_label(_with(sources=sources)) == "영상출처: MBC, JTBC"

    def test_summary_uses_narration_when_text_missing(self):
        """V5 TTS 씬은 text 가 선택이라 요약이 육성 자막만 돌려쓰던 버그 (043 파일럿 1호)."""
        block = chat_block(BASE)
        lines = block.split("3줄요약:")[1].split("해시태그")[0].strip().splitlines()
        assert len(lines) == 3 and len(set(lines)) == 3
        assert any("대반전" in ln or "선관위" in ln for ln in lines)

    def test_with_scene_text_is_immutable(self):
        out = with_scene_text(BASE)
        assert out["scenes"][1]["text"].startswith("밤새")
        assert "text" not in BASE["scenes"][1]
        assert out["scenes"][0]["text"] == BASE["scenes"][0]["text"]

    def test_chat_block_ab(self):
        block = chat_block(BASE)
        assert "제목 A:" in block and "제목 B:" in block
        assert "3줄요약" in block and "해시태그" in block


class TestBuildScript:
    def test_scenes(self):
        script = build_script(BASE, {0: 4.0})
        assert len(script.scenes) == 3
        assert script.scenes[0].voice_text == "" and script.scenes[0].hook is True
        assert script.scenes[1].voice_text.startswith("밤새")
        assert script.metadata.source_type == "political_pro"   # 정치 어두운 BGM 고정 경로
        assert script.audio.tts_script.count("밤새") == 1

    def test_tts_scene_without_text(self):
        script = build_script(_with(scenes=BASE["scenes"][1:]), {})
        assert script.scenes[0].text.startswith("밤새")

    def test_female_voice(self):
        assert VOICE_NAME in ("Kore", "Leda", "Aoede")


class TestReuseTts:
    """--reuse-tts — 화면만 고칠 때 Gemini TTS(일 10회)를 다시 쓰지 않는다."""

    def _write(self, d, stem, ids):
        import json as _json
        (d / f"{stem}.mp3").write_bytes(b"ID3")
        (d / f"{stem}.timing.json").write_text(_json.dumps(
            [{"scene_id": i, "start_ms": n * 1000, "end_ms": n * 1000 + 900}
             for n, i in enumerate(ids)]))

    def test_picks_newest_matching(self, tmp_path):
        import os
        from scripts.render_evidence_v5 import find_reusable_tts
        self._write(tmp_path, "old", [1, 2])
        self._write(tmp_path, "new", [1, 2])
        os.utime(tmp_path / "old.timing.json", (1, 1))
        mp3, timings = find_reusable_tts(tmp_path, {1, 2})
        assert mp3.name == "new.mp3" and [t["scene_id"] for t in timings] == [1, 2]

    def test_ignores_mismatched_scenes(self, tmp_path):
        from scripts.render_evidence_v5 import find_reusable_tts
        self._write(tmp_path, "a", [1, 3])
        assert find_reusable_tts(tmp_path, {1, 2}) is None

    def test_outro_id_ignored(self, tmp_path):
        from scripts.render_evidence_v5 import find_reusable_tts
        self._write(tmp_path, "a", [1, 2, -1])
        assert find_reusable_tts(tmp_path, {1, 2}) is not None

    def test_none_when_empty(self, tmp_path):
        from scripts.render_evidence_v5 import find_reusable_tts
        assert find_reusable_tts(tmp_path, {1}) is None
