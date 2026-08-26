"""039 Phase 5 — 게시 여부 판정 테스트.

**초기 2주는 전면 보류가 확정 정책이다** (사용자 선택, 2026-08-26). 저작권
스트라이크는 되돌릴 수 없어서, 사람이 승인하기 전에는 무엇도 공개되지 않는다.
"""
import json

from scripts.auto_daily.review_gate import (
    GatePolicy, clip_ratio, decide, load_gate_policy,
)


def _cfg(clip_secs=(4.0, 5.0), tts_secs=(3.0,)):
    scenes = [{"mode": "clip", "source": "main", "duration": d} for d in clip_secs]
    scenes += [{"mode": "tts", "source": "main", "voice": "가" * int(d * 7.4)}
               for d in tts_secs]
    return {"slug": "s", "title": "t", "sources": {"main": {}}, "scenes": scenes}


_OPEN = GatePolicy(always_hold=False, max_warnings=0, min_clip_ratio=0.65)


# ── 정책 로드 ───────────────────────────────────────────────────────
def test_정책파일이_없으면_전면보류가_기본값이다(tmp_path):
    assert load_gate_policy(tmp_path / "없음.json").always_hold is True


def test_정책파일을_읽는다(tmp_path):
    path = tmp_path / "gate.json"
    path.write_text(json.dumps({"always_hold": False, "max_warnings": 2}),
                    encoding="utf-8")
    policy = load_gate_policy(path)
    assert policy.always_hold is False
    assert policy.max_warnings == 2


def test_깨진_정책파일도_보류로_떨어진다(tmp_path):
    path = tmp_path / "gate.json"
    path.write_text("{ 망가짐", encoding="utf-8")
    assert load_gate_policy(path).always_hold is True


# ── 전면 보류 ───────────────────────────────────────────────────────
def test_전면보류면_흠이_없어도_보류한다():
    decision = decide(_cfg(), warnings=(), policy=GatePolicy(always_hold=True))
    assert decision.should_publish is False
    assert any("전면 보류" in r for r in decision.reasons)


def test_전면보류를_끄고_흠이_없으면_게시한다():
    assert decide(_cfg(), warnings=(), policy=_OPEN).should_publish is True


# ── 보류 사유 ───────────────────────────────────────────────────────
def test_경고가_있으면_보류한다():
    decision = decide(_cfg(), warnings=("길이 초과 추정",), policy=_OPEN)
    assert decision.should_publish is False
    assert any("길이 초과" in r for r in decision.reasons)


def test_허용_경고수_이내면_게시한다():
    policy = GatePolicy(always_hold=False, max_warnings=2, min_clip_ratio=0.65)
    assert decide(_cfg(), warnings=("사소한 경고",), policy=policy).should_publish is True


def test_클립비중이_낮으면_보류한다():
    """육성 릴레이인데 TTS 논평이 과반이면 V2.2 가 아니다."""
    decision = decide(_cfg(clip_secs=(2.0,), tts_secs=(10.0,)),
                      warnings=(), policy=_OPEN)
    assert decision.should_publish is False
    assert any("클립 비중" in r for r in decision.reasons)


def test_채널이_미등록이면_보류한다():
    decision = decide(_cfg(), warnings=(), policy=_OPEN, channel_registered=False)
    assert decision.should_publish is False
    assert any("채널" in r for r in decision.reasons)


def test_보류사유는_여러개_모인다():
    decision = decide(_cfg(clip_secs=(1.0,), tts_secs=(10.0,)),
                      warnings=("경고1",), policy=_OPEN, channel_registered=False)
    assert len(decision.reasons) >= 3


def test_config가_없으면_보류한다():
    """초안 작성이 실패한 경우."""
    assert decide(None, warnings=(), policy=_OPEN).should_publish is False


# ── 클립 비중 ───────────────────────────────────────────────────────
def test_클립비중을_계산한다():
    ratio = clip_ratio(_cfg(clip_secs=(6.0, 6.0), tts_secs=(3.0,)))
    assert 0.7 < ratio < 0.85


def test_클립이_없으면_비중은_0():
    assert clip_ratio(_cfg(clip_secs=(), tts_secs=(5.0,))) == 0.0


def test_씬이_없으면_비중은_0():
    assert clip_ratio({"scenes": []}) == 0.0
