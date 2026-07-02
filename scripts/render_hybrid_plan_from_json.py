"""Render a single HybridShortsPlan from plans_hybrid.json.

Usage:
    PYTHONPATH=. python3 scripts/render_hybrid_plan_from_json.py <plans_dir> <plan_idx>
        [--order "H,O1,T1,O2,T2,O3,T3,C"]

비트 식별자:
    H        Hook (TTS 첫 비트)
    C        CTA (TTS 마지막 비트)
    O1/O2/O3 plan.beats 안의 1/2/3번째 원본 비트
    T1/T2/T3 plan.beats 안의 1/2/3번째 TTS 논평 비트

--order 미지정 시 기본값 = 기존 plan.all_beats() 순서.

Pipeline:
    1. Load plans_hybrid.json, pick plan_idx (0/1/2)
    2. Parse --order → 비트 시퀀스
    3. Synthesize Charon TTS for ALL plan TTS beats (synthesis 순서는 plan 원본 순서)
    4. Each chunk: 사용자 지정 순서대로 TTS 슬라이스/원본 컷 + 자막 + 제목 띠
    5. Concat all chunks + public/outro.png
"""
from __future__ import annotations

import argparse
import json as _json
import os
import subprocess as _sub
import sys
import time as _time
from pathlib import Path

ROOT = Path("/Users/kyusik/ContentsMaker")
sys.path.insert(0, str(ROOT))

from src.analyzer.hybrid_plan_models import (  # noqa: E402
    HybridBeat,
    HybridShortsPlan,
    ThreeHybridPlansResult,
)
from src.analyzer.script_models import (  # noqa: E402
    AudioConfig,
    BackgroundConfig,
    Metadata,
    Scene,
    ShortsScript,
)
from src.tts.gemini_tts_generator import (  # noqa: E402
    generate_voice_with_timing_gemini,
)
from src.video.hybrid_renderer import (  # noqa: E402
    SubtitleStyle,
    build_original_beat,
    build_outro_from_image,
    build_tts_beat,
    concat_chunks,
    render_subtitle_png,
    render_title_banner_png,
)

# 사용자 락인 (2026-06-16): TTS는 1.2배 빠르게, 동일 비율로 화면·자막도 단축
TTS_SPEED = 1.2

# 제목 띠 (outro 제외 모든 비트에 지속 표시) — 영상별 수동 지정 또는 plan.topic에서 추출
TITLE_BANNER_OVERRIDE = "서울 포함 6곳 전면 재선거"

OUT_DIR_DEFAULT = ROOT / "data/political_pro/20260615_193552_cli"
SRC_OBS = OUT_DIR_DEFAULT / "_hUJOG82az0.mp4"
SRC_JANG = OUT_DIR_DEFAULT / "jang_dong_hyuk_xMZuzO3gXs4.mp4"

# Charon voice config — V2 락인과 동일
TTS_VOICE = "Charon"
TTS_STYLE = "Read in a fast, clear newscaster tone with neutral political delivery:"
TTS_TEMP = 0.5

# Jang 배경 컷 시작점 — 단상 깨끗하게 잡힌 구간 (TTS 비트마다 다른 컷)
JANG_OFFSETS = [60.0, 90.0, 200.0, 240.0, 300.0, 330.0, 360.0]


def _run(cmd: list[str]) -> None:
    print("$", " ".join(cmd[:4]), "...", file=sys.stderr)
    res = _sub.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr)
        raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:3])}")


def _synthesize_tts_via_script(
    *, tts_texts: list[str], title: str, work_dir: Path,
) -> tuple[Path, list[dict]]:
    """V2 검증 경로 사용 — TTS 비트마다 Scene 1개씩인 합성 ShortsScript를 만들어
    generate_voice_with_timing_gemini 로 1회 합성. 반환: (mp3 path, scene_timings).
    """
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("GEMINI_API_KEY 필요")

    # 한 비트 = 한 Scene (id = TTS 비트의 순번)
    scenes: list[Scene] = []
    cursor = 0.0
    for i, txt in enumerate(tts_texts):
        # 임의 duration (실제 길이는 합성 후 timing.json으로 결정됨)
        est = max(1.5, len(txt) / 5.0)
        scenes.append(Scene(
            id=i,
            timestamp=cursor,
            duration=est,
            type="body" if 0 < i < len(tts_texts) - 1 else (
                "title" if i == 0 else "comment"
            ),
            text=txt,
            voice_text=txt,
        ))
        cursor += est

    script = ShortsScript(
        metadata=Metadata(
            title=title,
            emotion_type="angry",
            duration=cursor,
            source_type="political_pro",
        ),
        scenes=tuple(scenes),
        audio=AudioConfig(
            tts_script=" ".join(tts_texts),
            voice="Charon", rate="+0%", pitch="+0Hz",
        ),
        background=BackgroundConfig(type="gradient", colors=("#1a1a2e", "#0f0f1e")),
    )
    print(f"🎙️ Charon 합성 — {len(tts_texts)}비트, {sum(len(t) for t in tts_texts)}자",
          file=sys.stderr)
    audio_path, timings = generate_voice_with_timing_gemini(
        script,
        output_dir=work_dir,
        voice_name=TTS_VOICE,
        api_key=key,
        include_outro=False,
        # style_prompt 일부 조합에서 Gemini가 instruction으로 오인 → 비우고 raw TTS만
        style_prompt=None,
        temperature=TTS_TEMP,
    )
    print(f"✅ TTS 합성 완료: {audio_path.name}", file=sys.stderr)
    return audio_path, timings


def _split_subtitle_lines(subtitle: str) -> tuple[str, ...]:
    """Plan에 저장된 'a / b / c' 자막을 줄 단위로 분할."""
    return tuple(s.strip() for s in subtitle.split("/") if s.strip())


def parse_order(order_str: str, plan: HybridShortsPlan) -> list[int]:
    """`--order` 문자열을 all_beats() 인덱스 리스트로 변환.

    토큰 → all_beats 인덱스 매핑:
        H        → 0 (hook)
        C        → len(all_beats) - 1 (cta)
        O<n>     → plan.beats 안의 n번째 원본 비트 (1-indexed)
        T<n>     → plan.beats 안의 n번째 TTS 논평 비트 (1-indexed)
    """
    all_beats = plan.all_beats()
    # plan.beats[i] (0-indexed) == all_beats[i + 1]
    orig_to_all_idx: list[int] = [
        i + 1 for i, b in enumerate(plan.beats) if b.kind == "original"
    ]
    tts_to_all_idx: list[int] = [
        i + 1 for i, b in enumerate(plan.beats) if b.kind == "tts"
    ]

    result: list[int] = []
    for raw in order_str.split(","):
        tok = raw.strip().upper()
        if tok == "H":
            result.append(0)
        elif tok == "C":
            result.append(len(all_beats) - 1)
        elif tok.startswith("O") and tok[1:].isdigit():
            n = int(tok[1:])
            if not (1 <= n <= len(orig_to_all_idx)):
                raise SystemExit(
                    f"❌ 토큰 {tok!r} — 원본 비트 {n}번 없음 (plan에 {len(orig_to_all_idx)}개)"
                )
            result.append(orig_to_all_idx[n - 1])
        elif tok.startswith("T") and tok[1:].isdigit():
            n = int(tok[1:])
            if not (1 <= n <= len(tts_to_all_idx)):
                raise SystemExit(
                    f"❌ 토큰 {tok!r} — TTS 논평 비트 {n}번 없음 (plan에 {len(tts_to_all_idx)}개)"
                )
            result.append(tts_to_all_idx[n - 1])
        else:
            raise SystemExit(
                f"❌ 토큰 {tok!r} 알 수 없음. 사용 가능: H, C, O<n>, T<n>"
            )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description="HybridShortsPlan 1개를 mp4로 렌더 (사용자 지정 비트 순서 지원)",
    )
    ap.add_argument("plans_dir", type=Path,
                    help="plans_hybrid.json + 소스 영상이 있는 디렉터리")
    ap.add_argument("plan_idx", type=int, choices=[0, 1, 2],
                    help="0=Plan 1 (title_anchor), 1=Plan 2 (audience_resonance), "
                         "2=Plan 3 (comparison)")
    ap.add_argument(
        "--order", type=str, default="",
        help="비트 순서 — 콤마 구분 토큰: H(Hook), C(CTA), O1/O2/O3(원본), T1/T2/T3(TTS). "
             "예: 'H,O1,T1,O2,T2,O3,T3,C'. 미지정 시 plan 기본 순서.",
    )
    args = ap.parse_args()
    out_dir = args.plans_dir.resolve()
    plan_idx = args.plan_idx

    plans_json = out_dir / "plans_hybrid.json"
    if not plans_json.exists():
        print(f"❌ plans_hybrid.json not found at {plans_json}", file=sys.stderr)
        return 2

    result = ThreeHybridPlansResult.from_dict(
        _json.loads(plans_json.read_text(encoding="utf-8"))
    )
    if plan_idx not in (0, 1, 2):
        print(f"❌ plan-idx 0/1/2 (got {plan_idx})", file=sys.stderr)
        return 2

    plan: HybridShortsPlan = result.plans[plan_idx]
    print(
        f"✅ Plan {plan_idx + 1} 선택 — angle={plan.angle}, "
        f"TTS={plan.tts_seconds:.1f}s, ORIG={plan.original_seconds:.1f}s",
        file=sys.stderr,
    )

    ts = int(_time.time())
    work_dir = out_dir / f"v3_plan{plan_idx}_{ts}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 제목 띠 PNG — outro 제외 모든 비트에 영구 overlay
    title_text = TITLE_BANNER_OVERRIDE or plan.topic.split(",")[-1].strip()[:18]
    title_png = work_dir / "title_banner.png"
    render_title_banner_png(text=title_text, out_path=title_png)
    print(f"📌 제목 띠: {title_text!r}", file=sys.stderr)

    # ─ 모든 TTS 비트의 tts_text를 plan 원본 순서대로 모아 1회 Charon 합성 ─
    # (출력 순서가 바뀌어도 합성 자체는 plan 순서 유지 → timing 일관성 보장)
    all_beats = plan.all_beats()
    tts_beats: list[HybridBeat] = [b for b in all_beats if b.kind == "tts"]
    tts_texts = [b.tts_text for b in tts_beats]
    tts_beat_order = [i for i, b in enumerate(all_beats) if b.kind == "tts"]

    # ─ 사용자 지정 비트 순서 결정 (--order 없으면 기본 = plan 순서) ─
    if args.order.strip():
        chunk_sequence = parse_order(args.order, plan)
        print(f"📐 사용자 지정 비트 순서: {args.order!r} → {chunk_sequence}",
              file=sys.stderr)
    else:
        chunk_sequence = list(range(len(all_beats)))
        print(f"📐 기본 비트 순서 (plan 원본): {chunk_sequence}", file=sys.stderr)

    tts_mp3, timings = _synthesize_tts_via_script(
        tts_texts=tts_texts,
        title=f"{plan.topic[:25]}_plan{plan_idx + 1}",
        work_dir=work_dir,
    )

    # timings: [{"scene_id": i, "start_ms": ..., "end_ms": ...}] — scene_id == TTS 순번
    timing_map = {t["scene_id"]: t for t in timings if t["scene_id"] != -1}
    tts_ranges: dict[int, tuple[float, float]] = {}  # all_beats 인덱스 → (start_s, end_s)
    for tts_idx_in_list, beat_idx in enumerate(tts_beat_order):
        t = timing_map.get(tts_idx_in_list)
        if t is None:
            raise SystemExit(f"TTS timing 누락 (scene_id={tts_idx_in_list})")
        tts_ranges[beat_idx] = (t["start_ms"] / 1000, t["end_ms"] / 1000)

    # ─ 각 비트를 chunk mp4로 ─
    chunks: list[Path] = []
    jang_offset_idx = 0

    last_all_idx = len(all_beats) - 1
    for i, beat_idx in enumerate(chunk_sequence):
        beat = all_beats[beat_idx]
        chunk_out = work_dir / f"{i:02d}_{beat.kind}_b{beat_idx}.mp4"
        sub_png = work_dir / f"{i:02d}_sub.png"

        if beat.kind == "tts":
            lines = _split_subtitle_lines(beat.subtitle)
            # Hook/CTA 식별은 plan 원본 인덱스 기준 (출력 순서가 바뀌어도 강조 유지)
            is_hook_or_cta = (beat_idx == 0) or (beat_idx == last_all_idx)
            render_subtitle_png(
                style=SubtitleStyle(
                    lines=lines,
                    color_name=beat.subtitle_color,
                    emphasis=beat.subtitle_emphasis or is_hook_or_cta,
                ),
                out_path=sub_png,
            )
            t_start, t_end = tts_ranges[beat_idx]
            jang_off = JANG_OFFSETS[jang_offset_idx % len(JANG_OFFSETS)]
            jang_offset_idx += 1
            # TTS 비트: 1.2배 속도 (음성·화면·자막 동기). 제목 띠 overlay.
            build_tts_beat(
                beat=beat,
                background_clip=SRC_JANG,
                background_offset_sec=jang_off,
                tts_audio_full=tts_mp3,
                tts_start_sec=t_start,
                tts_end_sec=t_end,
                subtitle_png=sub_png,
                out=chunk_out,
                title_banner_png=title_png,
                speed=TTS_SPEED,
            )
        else:  # original
            # quote_lines 전부 표시 (V3 lock-in: 추출 구간 발언 전체 커버)
            render_subtitle_png(
                style=SubtitleStyle(
                    lines=beat.quote_lines,
                    color_name="white",
                    emphasis=False,
                    bottom_label=beat.source_label,
                    y_center_frac=0.72 if len(beat.quote_lines) >= 3 else 0.74,
                ),
                out_path=sub_png,
            )
            # 원본 비트: 화자 음성 그대로 (속도 변경 X). 제목 띠 overlay.
            build_original_beat(
                beat=beat,
                source_clip=SRC_OBS,
                subtitle_png=sub_png,
                out=chunk_out,
                title_banner_png=title_png,
            )
        chunks.append(chunk_out)

    # ─ Outro (원본 outro.png) ─
    outro = work_dir / "99_outro.mp4"
    build_outro_from_image(
        image_path=ROOT / "public/outro.png",
        out=outro,
        duration=4.0,
        source_label=f"출처: {plan.source_channel} · {plan.source_title}",
    )
    chunks.append(outro)

    # ─ Concat ─
    final = out_dir / f"V3_HYBRID_plan{plan_idx + 1}_{plan.angle}_{ts}.mp4"
    print(f"🎬 concat {len(chunks)}개 청크 → {final.name}", file=sys.stderr)
    concat_chunks(chunks, final)
    print(f"✅ FINAL: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
