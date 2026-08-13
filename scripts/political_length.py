"""정치쇼츠 길이 게이트 (035) — 38~42초 캡.

**근거 (채널 실측 2026-08-05, 88편)**: 조회수 중앙값 1,169회에 900~1,400 구간이
47%로 몰려 있다. 제목 유형(hook 1,151 / neutral 1,200 / report 1,121)·제목 언어
(한글 1,150 / 영어 1,151)로는 차이가 없어, 병목은 클릭이 아니라 **완주율**이다.
상위권 2편(3,048회 38초 / 3,093회 40초)만 40초 이하였고 최근 40편 평균은 48초.

**추정 계수**: 기존 config 31개 × 렌더 결과 실측으로 보정 — 1.0배속 기준
중앙값 7.4자/초 (V2.1 19편 기준 1.1배속 8.1자/초). 추정 오차가 ±15% 있으므로
validate 단계는 **경고**만 하고, 렌더 단계에서 합성된 실제 오디오 길이로
**하드 차단**한다. config에 `"duration_gate": "off"` 를 넣으면 둘 다 우회.
"""
from __future__ import annotations

CHARS_PER_SEC_1X = 7.4      # 1.0배속 기준 Charon TTS 한국어 낭독 속도 (실측 중앙값)
DEFAULT_TTS_SPEED = 1.1     # V2.1/V2.2 표준 배속 (사용자 확정 2026-07-21)
TARGET_MIN_SEC = 38.0       # 권장 하한 (문서용 — 코드 경고는 하지 않는다)
TARGET_MAX_SEC = 42.0       # 하드 캡 (최종 mp4 기준 — 아웃트로 포함)
# ShortsComposition.tsx 의 OUTRO_DURATION_FRAMES = FPS * 4 — 렌더 시 항상 덧붙는다.
# 씬 타임라인만 재면 최종 파일이 캡을 넘긴다 (2026-08-05 실측: 타임라인 38.3s → 파일 42.3s).
OUTRO_SEC = 4.0


def _speed(cfg: dict) -> float:
    try:
        s = float(cfg.get("tts_speed", DEFAULT_TTS_SPEED))
    except (TypeError, ValueError):
        return DEFAULT_TTS_SPEED
    return s if s > 0 else DEFAULT_TTS_SPEED


def estimate_tts_sec(chars: int, speed: float = DEFAULT_TTS_SPEED) -> float:
    """나레이션 글자 수 → 예상 낭독 초. 배속이 빠를수록 짧아진다."""
    if chars <= 0:
        return 0.0
    return chars / (CHARS_PER_SEC_1X * speed)


def excess_chars(over_sec: float, speed: float = DEFAULT_TTS_SPEED) -> int:
    """초과 초 → 잘라내야 할 나레이션 글자 수."""
    if over_sec <= 0:
        return 0
    return int(round(over_sec * CHARS_PER_SEC_1X * speed))


def scene_duration_estimates(cfg: dict) -> list[float]:
    """cfg["scenes"] 순서대로 예상 길이(초).

    clip 씬은 선언된 duration, tts 씬은 voice 글자 수 추정.
    V2.1 씬은 `mode` 키가 없어 기본값 tts 로 처리된다.
    """
    scenes = cfg.get("scenes")
    if not isinstance(scenes, list):
        return []
    speed = _speed(cfg)
    out = []
    for sc in scenes:
        if sc.get("mode", "tts") == "clip":
            out.append(float(sc.get("duration", 3.0)))
        else:
            out.append(estimate_tts_sec(len(sc.get("voice", "")), speed))
    return out


def hook_offset_sec(cfg: dict) -> float:
    """V2.1 top-level hook(원본 육성) 길이. V2.2 는 씬으로 통일돼 0."""
    hook = cfg.get("hook") or {}
    try:
        return float(hook.get("duration", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def estimate_total_sec(cfg: dict) -> float:
    """씬 타임라인 예상 길이 (아웃트로 제외) — CTA 삽입 위치 계산에 쓰인다."""
    return hook_offset_sec(cfg) + sum(scene_duration_estimates(cfg))


def final_video_sec(timeline_sec: float) -> float:
    """시청자가 보는 최종 mp4 길이 = 씬 타임라인 + 아웃트로."""
    return timeline_sec + OUTRO_SEC


def _cut_hint(final_sec: float, cfg: dict) -> str:
    over = final_sec - TARGET_MAX_SEC
    return (f"약 {excess_chars(over, _speed(cfg))}자(≈{over:.1f}초)를 줄이거나 "
            f"씬 1개를 빼세요")


def length_warnings(cfg: dict) -> list[str]:
    """validate 단계 경고 (추정 기반). 캡 **초과만** 경고 — 짧은 건 문제가 아니다."""
    if cfg.get("duration_gate") == "off":
        return []
    final = final_video_sec(estimate_total_sec(cfg))
    if final <= TARGET_MAX_SEC:
        return []
    return [f"예상 최종 길이 {final:.1f}초 (씬 {final - OUTRO_SEC:.1f}s + 아웃트로 "
            f"{OUTRO_SEC:.0f}s) > 캡 {TARGET_MAX_SEC:.0f}초 — "
            f"{_cut_hint(final, cfg)} (035, 추정 오차 ±15%)"]


def enforce_length(timeline_sec: float, cfg: dict) -> None:
    """렌더 단계 하드 게이트 — 합성된 실제 타임라인 + 아웃트로로 판정."""
    if cfg.get("duration_gate") == "off":
        return
    final = final_video_sec(timeline_sec)
    if final <= TARGET_MAX_SEC:
        return
    raise ValueError(
        f"최종 길이 {final:.1f}초 (씬 {timeline_sec:.1f}s + 아웃트로 {OUTRO_SEC:.0f}s) "
        f"> 캡 {TARGET_MAX_SEC:.0f}초 (035 완주율 게이트) — "
        f"{_cut_hint(final, cfg)}. "
        f"권장 구간 {TARGET_MIN_SEC:.0f}~{TARGET_MAX_SEC:.0f}초. "
        '우회: config에 "duration_gate": "off"'
    )


__all__ = [
    "CHARS_PER_SEC_1X", "DEFAULT_TTS_SPEED", "TARGET_MIN_SEC", "TARGET_MAX_SEC",
    "enforce_length", "estimate_total_sec", "estimate_tts_sec", "excess_chars",
    "hook_offset_sec", "length_warnings", "scene_duration_estimates",
]
