"""ad-hoc 단일 클립 추출기 — 사용자가 지정한 [start, end] 구간을 9:16 letterbox로
잘라서 원본 음성 + Noto Sans KR 자막을 입혀 단독 mp4로 저장한다.

V3 hybrid_renderer의 build_original_beat_timed_subs / render_subtitle_png를 재사용.

────────────────────────────────────────────────────────────────────────────────
지침 (2026-06-16 락인) — 자막은 추출 구간 전체 발언을 다 보여야 한다
────────────────────────────────────────────────────────────────────────────────

추출 구간 [start, end] 안에서 화자가 말하는 내용 전체가 자막으로 다 나와야 한다.
도입부 한 줄만 띄우고 멈추면 클라이맥스 발언이 묻혀 호응이 떨어진다.

방법:
1. transcript.json (또는 ASR 분석)에서 [start, end]에 걸친 모든 발언 추출
2. 발언을 2~3개의 짧은 카드로 분할 (각 카드 = 보도체 paraphrase, ≤21자/줄, ≤2~3줄)
3. ffmpeg overlay enable='between(t,a,b)'로 클립 내 시간 따라 자막 교체
4. 각 카드는 약 3~4초 표시 (시청자가 읽을 수 있는 최소 시간)
5. 마지막 카드는 클립 끝까지 (`end - start`)로 잡아 메시지 누락 방지

예시 — OBS [8, 16] 구간:
    - 8~12초 (OBS): "오늘 국민의힘은 어 소청 관련된 논의를 했었고요"
    - 12~16초 (OBS): "결론을 먼저 말씀드리면 전면 재선거를 하기로..."
    → 자막 카드 2장:
        (0~4s 클립) "오늘 국민의힘은 소청 관련 / 논의를 했습니다"
        (4~8s 클립) "결론을 먼저 말씀드리면 / 전면 재선거를 하기로..."

────────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
import time as _time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("/Users/kyusik/ContentsMaker")
sys.path.insert(0, str(ROOT))

from src.analyzer.hybrid_plan_models import HybridBeat  # noqa: E402
from src.video.hybrid_renderer import (  # noqa: E402
    SubtitleStyle,
    build_original_beat_timed_subs,
    render_subtitle_png,
)

OUT_DIR = ROOT / "data/political_pro/20260615_193552_cli"
SRC_OBS = OUT_DIR / "_hUJOG82az0.mp4"


@dataclass(frozen=True)
class TimedCard:
    """클립 내 상대 시간으로 표시할 자막 카드."""
    start_rel_sec: float
    end_rel_sec: float
    lines: tuple[str, ...]
    bottom_label: str = ""


def main() -> int:
    # ──────────────────── 사용자 지정 구간 ────────────────────
    start, end = 8.0, 16.0
    speaker_label = "— 국민의힘 대변인 (OBS뉴스)"

    # ──────────────────── 자막 카드 (구간 전체 커버) ────────────────────
    # 위 지침에 따라 [8, 16] 안의 발언을 2장 카드로 분할.
    cards: list[TimedCard] = [
        TimedCard(
            start_rel_sec=0.0,
            end_rel_sec=4.0,
            lines=("오늘 국민의힘은 소청 관련", "논의를 했습니다"),
            bottom_label=speaker_label,
        ),
        TimedCard(
            start_rel_sec=4.0,
            end_rel_sec=end - start,   # 클립 끝까지 잡아 메시지 누락 방지
            lines=("결론을 먼저 말씀드리면", "전면 재선거를 하기로..."),
            bottom_label=speaker_label,
        ),
    ]
    # ─────────────────────────────────────────────────────────────────

    beat = HybridBeat(
        kind="original",
        duration_sec=end - start,
        clip_start_sec=start,
        clip_end_sec=end,
        speaker_name="국민의힘 대변인",
        # quote_lines는 모델 검증용 (첫 카드 사용)
        quote_lines=cards[0].lines,
        bgm_mode="mute",
        source_label=speaker_label,
    )

    ts = int(_time.time())
    work_dir = OUT_DIR / f"clip_{ts}"
    work_dir.mkdir(parents=True, exist_ok=True)

    timed_subs: list[tuple[float, float, Path]] = []
    for i, card in enumerate(cards):
        png = work_dir / f"sub_{i:02d}.png"
        render_subtitle_png(
            style=SubtitleStyle(
                lines=card.lines,
                color_name="white",
                emphasis=False,
                bottom_label=card.bottom_label,
            ),
            out_path=png,
        )
        timed_subs.append((card.start_rel_sec, card.end_rel_sec, png))

    out_mp4 = OUT_DIR / f"OBS_clip_{int(start)}_{int(end)}s_{ts}.mp4"
    build_original_beat_timed_subs(
        beat=beat,
        source_clip=SRC_OBS,
        timed_subs=timed_subs,
        out=out_mp4,
    )
    print(
        f"✅ {out_mp4} — 카드 {len(cards)}장 "
        f"({', '.join(f'{c.start_rel_sec:.1f}~{c.end_rel_sec:.1f}s' for c in cards)})",
        file=sys.stderr,
    )
    print(str(out_mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
