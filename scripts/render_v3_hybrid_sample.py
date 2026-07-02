"""V3 하이브리드 정치쇼츠 1차 산출물 — 같은 OBS+장동혁 소스에 V3 포맷 적용.

수동으로 HybridShortsPlan 작성 (다음 세션에서 Phase B LLM 자동화로 교체).
캐시된 Charon TTS 오디오를 재사용해 변동 회피.
"""
from __future__ import annotations

import sys
import time as _time
from pathlib import Path

ROOT = Path("/Users/kyusik/ContentsMaker")
sys.path.insert(0, str(ROOT))

from src.analyzer.hybrid_plan_models import (  # noqa: E402
    HybridBeat,
    HybridShortsPlan,
)
from src.video.hybrid_renderer import (  # noqa: E402
    SubtitleStyle,
    build_original_beat,
    build_outro_from_image,
    build_tts_beat,
    concat_chunks,
    render_subtitle_png,
)

OUT_DIR = ROOT / "data/political_pro/20260615_193552_cli"
SRC_OBS = OUT_DIR / "_hUJOG82az0.mp4"
SRC_JANG = OUT_DIR / "jang_dong_hyuk_xMZuzO3gXs4.mp4"
TTS_AUDIO = (
    ROOT
    / "data/audio/20260615_195349_민주당_지지율_하락_읽고_던진_국민의힘의_전면_재선거.mp3"
)


def build_sample_plan() -> HybridShortsPlan:
    """수동 HybridShortsPlan — 듀레이션은 캐시된 Charon timing.json과 정확히 일치."""
    # Hook (TTS): Charon scene 0 (0–3.213s)
    hook = HybridBeat(
        kind="tts", duration_sec=3.213,
        subtitle="민주당 지지율 빠졌다 / 국민의힘 신의 한 수",
        tts_text="(cached)",
        subtitle_color="yellow", subtitle_emphasis=True,
    )
    # B1 (original): OBS [13.0, 18.5] — 대변인 "전면 재선거를 하기로 결정되었습니다"
    b1 = HybridBeat(
        kind="original", duration_sec=5.5,
        clip_start_sec=13.0, clip_end_sec=18.5,
        speaker_name="국민의힘 대변인",
        quote_lines=("전면 재선거를 하기로", "결정되었습니다"),
        bgm_mode="mute",
        source_label="— 국민의힘 대변인 (OBS뉴스)",
    )
    # B2 (TTS): Charon scenes 1+2 (3.213–9.372s = 6.159s)
    b2 = HybridBeat(
        kind="tts", duration_sec=6.159,
        subtitle="민주당 지지율 슬그머니 하락 / 그 신호를 읽어낸 국민의힘",
        tts_text="(cached)",
        subtitle_color="red", subtitle_emphasis=True,
    )
    # B3 (original): OBS [88.5, 100.5] — "재선거에 대해 의견은... 결론에는 모두 동의했습니다"
    b3 = HybridBeat(
        kind="original", duration_sec=12.0,
        clip_start_sec=88.5, clip_end_sec=100.5,
        speaker_name="국민의힘 대변인",
        quote_lines=(
            "재선거에 대해",
            "의견은 조금씩 달랐지만",
            "결론에는 모두 동의했습니다",
        ),
        bgm_mode="mute",
        source_label="— 국민의힘 대변인 (OBS뉴스)",
    )
    # B4 (TTS): Charon scenes 5+6 (15.397–22.092s = 6.695s)
    b4 = HybridBeat(
        kind="tts", duration_sec=6.695,
        subtitle="정국 주도권 탈환 / 결단력 평가 한 방에 뒤집었다",
        tts_text="(cached)",
        subtitle_color="red", subtitle_emphasis=True,
    )
    # CTA (TTS): Charon scene 7 (22.092–24.770s = 2.678s)
    cta = HybridBeat(
        kind="tts", duration_sec=2.678,
        subtitle="이번 결단 / 신의 한 수 같으신가요?",
        tts_text="(cached)",
        subtitle_color="yellow", subtitle_emphasis=True,
    )

    return HybridShortsPlan(
        topic="민주당 지지율 하락 읽고 던진 국민의힘의 신의 한 수 (하이브리드)",
        hook=hook,
        beats=(b1, b2, b3, b4),
        cta=cta,
        angle="title_anchor",
        source_url="https://m.youtube.com/watch?v=_hUJOG82az0",
        source_channel="OBS뉴스",
        source_title="[현장영상] 오세훈 당선된 '서울' 포함 국민의힘 '전면 재선거' 소청",
    )


# ─── 빌드 순서 ─────────────────────────────────────────────────────────────────


def _subtitle_from_text(
    text: str, *, color: str, emphasis: bool, bottom_label: str = "",
) -> SubtitleStyle:
    """파이프(' / ')로 구분된 자막을 SubtitleStyle로 변환."""
    lines = tuple(s.strip() for s in text.split("/") if s.strip())
    return SubtitleStyle(
        lines=lines,
        color_name=color,
        emphasis=emphasis,
        bottom_label=bottom_label,
    )


def main() -> int:
    ts = int(_time.time())
    plan = build_sample_plan()
    print(
        f"✅ HybridPlan — TTS={plan.tts_seconds:.1f}s, "
        f"ORIG={plan.original_seconds:.1f}s, TOTAL={plan.total_seconds:.1f}s",
        file=sys.stderr,
    )

    work_dir = OUT_DIR / f"v3_{ts}"
    work_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[Path] = []

    # ─ Hook ─────────────────────────────────────────────────────────────────
    hook_sub = work_dir / "hook_sub.png"
    render_subtitle_png(
        style=_subtitle_from_text(
            plan.hook.subtitle, color="yellow", emphasis=True,
        ),
        out_path=hook_sub,
    )
    hook_mp4 = work_dir / "00_hook.mp4"
    build_tts_beat(
        beat=plan.hook,
        background_clip=SRC_JANG, background_offset_sec=60.0,
        tts_audio_full=TTS_AUDIO, tts_start_sec=0.0, tts_end_sec=3.213,
        subtitle_png=hook_sub, out=hook_mp4,
    )
    chunks.append(hook_mp4)

    # ─ B1: 원본 ─ "전면 재선거를 하기로 결정되었습니다"
    b1 = plan.beats[0]
    b1_sub = work_dir / "b1_sub.png"
    render_subtitle_png(
        style=SubtitleStyle(
            lines=b1.quote_lines,
            color_name="white", emphasis=False,
            bottom_label=b1.source_label,
        ),
        out_path=b1_sub,
    )
    b1_mp4 = work_dir / "01_orig_decision.mp4"
    build_original_beat(beat=b1, source_clip=SRC_OBS, subtitle_png=b1_sub, out=b1_mp4)
    chunks.append(b1_mp4)

    # ─ B2: TTS 논평 1 (scenes 1+2 from cached audio)
    b2 = plan.beats[1]
    b2_sub = work_dir / "b2_sub.png"
    render_subtitle_png(
        style=_subtitle_from_text(b2.subtitle, color="red", emphasis=True),
        out_path=b2_sub,
    )
    b2_mp4 = work_dir / "02_tts_comm1.mp4"
    build_tts_beat(
        beat=b2,
        background_clip=SRC_JANG, background_offset_sec=63.5,
        tts_audio_full=TTS_AUDIO, tts_start_sec=3.213, tts_end_sec=9.372,
        subtitle_png=b2_sub, out=b2_mp4,
    )
    chunks.append(b2_mp4)

    # ─ B3: 원본 ─ "재선거에 대해 / 의견은 조금씩 달랐지만 / 결론에는 모두 동의했습니다"
    b3 = plan.beats[2]
    b3_sub = work_dir / "b3_sub.png"
    render_subtitle_png(
        style=SubtitleStyle(
            lines=b3.quote_lines,
            color_name="white", emphasis=False,
            bottom_label=b3.source_label,
            y_center_frac=0.72,
        ),
        out_path=b3_sub,
    )
    b3_mp4 = work_dir / "03_orig_agreement.mp4"
    build_original_beat(beat=b3, source_clip=SRC_OBS, subtitle_png=b3_sub, out=b3_mp4)
    chunks.append(b3_mp4)

    # ─ B4: TTS 논평 2 (scenes 5+6)
    b4 = plan.beats[3]
    b4_sub = work_dir / "b4_sub.png"
    render_subtitle_png(
        style=_subtitle_from_text(b4.subtitle, color="red", emphasis=True),
        out_path=b4_sub,
    )
    b4_mp4 = work_dir / "04_tts_comm2.mp4"
    build_tts_beat(
        beat=b4,
        background_clip=SRC_JANG, background_offset_sec=240.0,
        tts_audio_full=TTS_AUDIO, tts_start_sec=15.397, tts_end_sec=22.092,
        subtitle_png=b4_sub, out=b4_mp4,
    )
    chunks.append(b4_mp4)

    # ─ CTA ──────────────────────────────────────────────────────────────────
    cta_sub = work_dir / "cta_sub.png"
    render_subtitle_png(
        style=_subtitle_from_text(plan.cta.subtitle, color="yellow", emphasis=True),
        out_path=cta_sub,
    )
    cta_mp4 = work_dir / "05_cta.mp4"
    build_tts_beat(
        beat=plan.cta,
        background_clip=SRC_JANG, background_offset_sec=300.0,
        tts_audio_full=TTS_AUDIO, tts_start_sec=22.092, tts_end_sec=24.770,
        subtitle_png=cta_sub, out=cta_mp4,
    )
    chunks.append(cta_mp4)

    # ─ Outro (원본 outro.png 사용) ─────────────────────────────────────────
    outro_mp4 = work_dir / "06_outro.mp4"
    build_outro_from_image(
        image_path=ROOT / "public/outro.png",
        out=outro_mp4,
        duration=4.0,
        source_label=f"출처: {plan.source_channel} · Channel A 기자회견",
    )
    chunks.append(outro_mp4)

    # ─ Concat ───────────────────────────────────────────────────────────────
    final = OUT_DIR / f"V3_HYBRID_sample_{ts}.mp4"
    print(f"🎬 concat {len(chunks)}개 청크 → {final.name}", file=sys.stderr)
    concat_chunks(chunks, final)
    print(f"✅ V3 FINAL: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
