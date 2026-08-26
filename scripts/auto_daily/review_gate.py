"""039 Phase 5 — 게시 여부 판정.

**초기 2주 전면 보류가 확정 정책이다** (사용자 선택, 2026-08-26). 렌더까지는
무인으로 가되 업로드 직전에 멈추고 알림을 보낸다. 사람이 승인해야 공개된다.

이유는 저작권이다. 방송 육성 클립을 무인으로 하루 3편 올리면 Content ID
클레임과 스트라이크가 사람 검수 없이 누적되고, 그건 채널을 통째로 날릴 수 있는
유일한 항목이다. 채택률과 클레임 통계를 확인한 뒤 `always_hold` 를 끈다.

게이트가 막지 못하는 것도 분명히 해둔다 — **밋밋한 훅과 어색한 자막 카피는
여기서 걸리지 않는다.** 그건 보류 기간 동안 사람이 재는 값이다.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

GATE_POLICY_PATH = PROJECT_ROOT / "data" / "auto_daily" / "review_policy.json"
#: V2.2 는 육성 릴레이다 — 클립 오디오 비중 하한 (렌더러의 CLIP_RATIO_MIN 과 동일)
DEFAULT_MIN_CLIP_RATIO = 0.65
CHARS_PER_SEC = 7.4


@dataclass(frozen=True)
class GatePolicy:
    always_hold: bool = True
    max_warnings: int = 0
    min_clip_ratio: float = DEFAULT_MIN_CLIP_RATIO


@dataclass(frozen=True)
class Decision:
    should_publish: bool
    reasons: tuple[str, ...]


def load_gate_policy(path: Path | None = None) -> GatePolicy:
    """정책 파일 로드. 없거나 깨졌으면 **보류**로 떨어진다."""
    target = Path(path) if path is not None else GATE_POLICY_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("게시 정책을 읽지 못해 전면 보류한다 (%s): %s", target, exc)
        return GatePolicy()
    return GatePolicy(
        always_hold=bool(raw.get("always_hold", True)),
        max_warnings=int(raw.get("max_warnings", 0)),
        min_clip_ratio=float(raw.get("min_clip_ratio", DEFAULT_MIN_CLIP_RATIO)),
    )


def _scene_seconds(scene: dict) -> float:
    """클립은 duration, TTS 는 나레이션 글자 수로 추정."""
    if scene.get("mode") == "clip":
        return float(scene.get("duration", 0.0))
    return len(scene.get("voice", "") or "") / CHARS_PER_SEC


def clip_ratio(cfg: dict) -> float:
    """원본 육성이 차지하는 비중. V2.2 의 정체성이라 낮으면 포맷이 깨진 것이다."""
    scenes = (cfg or {}).get("scenes") or []
    total = sum(_scene_seconds(s) for s in scenes)
    if total <= 0:
        return 0.0
    clip = sum(_scene_seconds(s) for s in scenes if s.get("mode") == "clip")
    return clip / total


def decide(cfg: dict | None, *, warnings: tuple[str, ...] = (),
           policy: GatePolicy | None = None,
           channel_registered: bool = True) -> Decision:
    """게시할지 보류할지. 보류 사유는 **전부** 모아서 알림에 싣는다."""
    policy = policy or GatePolicy()
    reasons: list[str] = []

    if cfg is None:
        return Decision(False, ("초안 작성 실패 — 게시할 config 가 없습니다",))
    if policy.always_hold:
        reasons.append("정책상 전면 보류 (초기 운영 기간) — 승인 후 수동 게시")
    if len(warnings) > policy.max_warnings:
        reasons.append(f"게이트 경고 {len(warnings)}건: " + " / ".join(warnings[:3]))
    ratio = clip_ratio(cfg)
    if ratio < policy.min_clip_ratio:
        reasons.append(
            f"클립 비중 {ratio:.0%} < 하한 {policy.min_clip_ratio:.0%} "
            "— 육성 릴레이(V2.2) 포맷이 아닙니다")
    if not channel_registered:
        reasons.append("원본 채널이 화이트리스트에 없습니다 (037-3)")

    return Decision(not reasons, tuple(reasons))
