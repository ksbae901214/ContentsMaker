"""039 Phase 3 — config 자동 작성 + 게이트 재시도 루프 테스트.

LLM 호출은 전부 주입한다. 검증하는 것은 **게이트 루프의 행동**이지 문장 품질이
아니다 — 품질은 초기 2주 보류 기간의 채택률로 측정한다.
"""
import json

import pytest

from scripts.auto_daily.config_drafter import (
    MAX_ATTEMPTS, DraftResult, build_prompt, check_config, draft_with_gates,
    extract_json,
)
from scripts.auto_daily.cut_planner import Cut
from scripts.auto_daily.naver_metrics import Article
from scripts.auto_daily.source_finder import SourceCandidate
from scripts.auto_daily.topic_ranker import TopicCluster

CUTS = [Cut(0.0, 4.0, "저는 사퇴하지 않습니다"),
        Cut(4.5, 5.0, "당의 결정을 따르겠습니다")]
CANDIDATE = SourceCandidate(video_id="abc12345678", title="기자회견 전체",
                            channel="KBS News", duration=600,
                            url="https://www.youtube.com/watch?v=abc12345678")


def _topic(headline="장동혁 대표직 사퇴", anchor="장동혁"):
    art = Article(title=headline,
                  link="https://n.news.naver.com/mnews/article/001/0000000001",
                  metric=900)
    return TopicCluster(anchor=anchor, articles=(art,), total_metric=900,
                        has_outcome=True, warnings=())


def _valid_config():
    return {
        "category": "political",
        "slug": "20260826_test_v2_2",
        "title": "상단 제목",
        "yt_title": "13시간 만에 뒤집힌 사퇴",
        "persons": ["장동혁"],
        "emotion_type": "angry",
        "source_channel": "KBS News",
        "youtube_url": CANDIDATE.url,
        "sources": {"main": {"query": "장동혁 기자회견", "dur_max": 900}},
        "scenes": [
            {"mode": "clip", "source": "main", "start_sec": 0.0, "duration": 4.0,
             "text": "\"저는 사퇴하지\n않습니다\"", "hl": ["사퇴"]},
            {"mode": "clip", "source": "main", "start_sec": 4.5, "duration": 5.0,
             "text": "13시간 만의\n번복", "hl": ["번복"]},
            {"mode": "tts", "source": "main", "frac": 0.5, "color": "yellow",
             "text": "결국\n대표직 사퇴", "voice": "장동혁 대표는 13시간 만에 사퇴했습니다.",
             "hl": ["사퇴"]},
            {"mode": "tts", "source": "main", "frac": 0.6, "color": "yellow",
             "text": "누구 책임일까요?\n① 당 ② 본인",
             "voice": "1번 당, 2번 본인. 댓글로 알려주세요.", "hl": ["책임"]},
        ],
    }


# ── JSON 추출 ───────────────────────────────────────────────────────
def test_코드펜스_안의_JSON을_뽑는다():
    text = '설명입니다\n```json\n{"a": 1}\n```\n끝'
    assert extract_json(text) == {"a": 1}


def test_펜스없는_JSON도_뽑는다():
    assert extract_json('앞말 {"a": 2} 뒷말') == {"a": 2}


def test_중첩된_객체도_끝까지_잡는다():
    assert extract_json('{"a": {"b": [1, 2]}, "c": 3}')["a"]["b"] == [1, 2]


def test_JSON이_없으면_ValueError():
    with pytest.raises(ValueError, match="JSON"):
        extract_json("죄송하지만 만들 수 없습니다")


# ── 게이트 검사 ─────────────────────────────────────────────────────
def test_정상_config는_오류가_없다():
    errors, _ = check_config(_valid_config())
    assert errors == []


def test_보도체_제목은_하드오류다():
    """034 게이트 — 과거형 어미로 끝나는 제목은 렌더가 막힌다."""
    cfg = _valid_config()
    cfg["yt_title"] = "장동혁 대표가 13시간 만에 사퇴했다"
    errors, _ = check_config(cfg)
    assert errors


def test_경제_투자권유는_하드오류다():
    """036 — 유사투자자문 소지. 우회는 config 로만 가능해야 한다."""
    cfg = _valid_config()
    cfg["category"] = "economic"
    cfg["yt_title"] = "결국 동결된 금리"
    cfg["scenes"][2]["voice"] = "지금이 매수 타이밍입니다. 존버하세요."
    errors, _ = check_config(cfg)
    assert errors


def test_없는_source를_가리키면_하드오류다():
    cfg = _valid_config()
    cfg["scenes"][0]["source"] = "없는소스"
    errors, _ = check_config(cfg)
    assert errors


def test_필수키_누락은_하드오류다():
    cfg = _valid_config()
    del cfg["scenes"]
    assert check_config(cfg)[0]


def test_길이초과는_경고로_잡힌다():
    """035 캡 — validate 단계에서는 추정 경고, 렌더 단계에서 하드 차단."""
    cfg = _valid_config()
    cfg["scenes"][2]["voice"] = "아주 긴 나레이션입니다. " * 40
    _, warnings = check_config(cfg)
    assert warnings


def test_CTA_종결이_명사형이면_경고():
    """'번호로 답글.' 은 부탁이 아니라 지시로 들린다."""
    cfg = _valid_config()
    cfg["scenes"][-1]["voice"] = "1번 당, 2번 본인. 번호로 답글."
    _, warnings = check_config(cfg)
    assert any("댓글로 알려주세요" in w or "종결" in w for w in warnings)


# ── 프롬프트 ────────────────────────────────────────────────────────
def test_프롬프트에_소재와_컷후보가_들어간다():
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="political",
                          slug="20260826_test_v2_2")
    assert "장동혁 대표직 사퇴" in prompt
    assert "저는 사퇴하지 않습니다" in prompt
    assert "4.0" in prompt


def test_프롬프트에_훅규칙이_명시된다():
    """훅은 시간순이 아니라 세기순 1등 — 무인 운영에서 가장 자주 틀리는 지점."""
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="political",
                          slug="s")
    assert "세기" in prompt or "가장 센" in prompt


def test_프롬프트에_CTA_종결규칙이_명시된다():
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="political", slug="s")
    assert "댓글로 알려주세요" in prompt


def test_경제_프롬프트는_투자권유_금지를_알린다():
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="economic", slug="s")
    assert "매수" in prompt


def test_프롬프트에_실패사유가_되먹여진다():
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="political", slug="s",
                          feedback=["yt_title 이 보도체입니다"])
    assert "yt_title 이 보도체입니다" in prompt


def test_카테고리별_결과어_예시가_들어간다():
    econ = build_prompt(_topic(), CANDIDATE, CUTS, category="economic", slug="s")
    ent = build_prompt(_topic(), CANDIDATE, CUTS, category="entertainment", slug="s")
    assert econ != ent


# ── 재시도 루프 ─────────────────────────────────────────────────────
def test_첫시도에_통과하면_한_번만_호출한다():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return json.dumps(_valid_config(), ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="20260826_test_v2_2", llm=fake_llm)
    assert result.ok is True
    assert result.attempts == 1
    assert len(calls) == 1


def test_실패하면_사유를_붙여_재시도한다():
    prompts = []

    def fake_llm(prompt):
        prompts.append(prompt)
        cfg = _valid_config()
        if len(prompts) == 1:
            cfg["yt_title"] = "장동혁 대표가 사퇴했다"     # 보도체 — 차단
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=fake_llm)
    assert result.ok is True
    assert result.attempts == 2
    assert "이전 시도" in prompts[1]


def test_계속_실패하면_최대횟수에서_멈춘다():
    def bad_llm(prompt):
        cfg = _valid_config()
        cfg["yt_title"] = "장동혁 대표가 사퇴했다"
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=bad_llm)
    assert result.ok is False
    assert result.attempts == MAX_ATTEMPTS
    assert result.errors


def test_JSON이_아니면_그것도_재시도_사유가_된다():
    calls = []

    def flaky_llm(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return "죄송합니다 만들 수 없습니다"
        return json.dumps(_valid_config(), ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=flaky_llm)
    assert result.ok is True
    assert result.attempts == 2


def test_LLM_예외도_삼키고_실패로_돌려준다():
    """슬롯 하나가 죽어도 나머지 슬롯은 돌아야 한다."""
    def boom(prompt):
        raise OSError("claude cli 없음")

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=boom)
    assert result.ok is False
    assert result.config is None


def test_슬러그와_출처가_강제로_주입된다():
    """LLM 이 채널명·URL 을 지어내면 저작권 추적이 끊긴다."""
    def fake_llm(prompt):
        cfg = _valid_config()
        cfg["slug"] = "엉뚱한슬러그"
        cfg["source_channel"] = "지어낸채널"
        cfg["youtube_url"] = "https://www.youtube.com/watch?v=zzzzzzzzzzz"
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="20260826_forced_v2_2", llm=fake_llm)
    assert result.config["slug"] == "20260826_forced_v2_2"
    assert result.config["source_channel"] == "KBS News"
    assert result.config["youtube_url"] == CANDIDATE.url


def test_카테고리도_강제로_주입된다():
    def fake_llm(prompt):
        cfg = _valid_config()
        cfg["category"] = "political"
        cfg["yt_title"] = "결국 동결된 금리"
        cfg["scenes"][2]["voice"] = "한국은행이 기준금리를 동결했습니다."
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="economic",
                              slug="s", llm=fake_llm)
    assert result.config["category"] == "economic"


def test_DraftResult는_불변이다():
    r = DraftResult(config=None, attempts=1, errors=(), warnings=(), ok=False)
    with pytest.raises(Exception):
        r.ok = True  # type: ignore[misc]


# ── 원본 고정 (컷 타임스탬프 무결성) ────────────────────────────────
def test_sources는_검색어가_아니라_정확한_URL로_고정된다():
    """검색어를 남기면 렌더러가 같은 검색으로 **다른 영상**을 받아올 수 있다.

    그러면 모든 클립이 엉뚱한 구간을 가리킨다 — 렌더는 성공하고 내용만 틀린다.
    """
    def fake_llm(prompt):
        cfg = _valid_config()
        cfg["sources"] = {"main": {"query": "아무 검색어", "dur_max": 900}}
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=fake_llm)
    assert result.config["sources"]["main"]["url"] == CANDIDATE.url
    assert "query" not in result.config["sources"]["main"]


def test_여러_소스를_써도_하나로_합쳐진다():
    def fake_llm(prompt):
        cfg = _valid_config()
        cfg["sources"] = {"a": {"query": "x"}, "b": {"query": "y"}}
        for scene in cfg["scenes"]:
            scene["source"] = "a"
        return json.dumps(cfg, ensure_ascii=False)

    result = draft_with_gates(_topic(), CANDIDATE, CUTS, category="political",
                              slug="s", llm=fake_llm)
    assert list(result.config["sources"]) == ["main"]
    assert {s["source"] for s in result.config["scenes"]} == {"main"}


def test_원본보다_긴_dur_max를_준다():
    """dur_max 가 원본 길이보다 짧으면 yt-dlp match-filter 가 전부 걸러낸다."""
    def fake_llm(prompt):
        return json.dumps(_valid_config(), ensure_ascii=False)

    long_candidate = SourceCandidate(video_id="x" * 11, title="긴 회견",
                                     channel="KBS News", duration=3000,
                                     url="https://www.youtube.com/watch?v=" + "x" * 11)
    result = draft_with_gates(_topic(), long_candidate, CUTS,
                              category="political", slug="s", llm=fake_llm)
    assert result.config["sources"]["main"]["dur_max"] > 3000


def test_프롬프트가_훅_10초_상한을_알린다():
    """모르면 12초 컷을 훅에 놓고 게이트에 걸려 재시도를 낭비한다."""
    prompt = build_prompt(_topic(), CANDIDATE, CUTS, category="political", slug="s")
    assert "10.0초" in prompt
