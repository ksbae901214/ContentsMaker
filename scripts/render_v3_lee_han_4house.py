"""V3 하이브리드 정치쇼츠 렌더 — 이재명 다주택 배제 vs 한성숙 4주택 모순 (2026-06-17).

기존 scripts/render_hybrid_plan_from_json.py의 변형판.
변경점 (surgical):
  - SRC_OBS / SRC_JANG / JANG_OFFSETS 하드코딩 제거
  - 각 original 비트의 ``beat.source_clip_path``를 work_dir 상대경로로 해석
  - Hook 배경: ``plan.extra_clip_sources['_hook_background_clip']`` +
    ``_hook_background_offset_sec``
  - T1/T2/CTA 배경: 같은 hook 영상의 다른 offset(10s/90s/120s 순환)
  - 제목 띠: ``TITLE_BANNER`` env > extra_clip_sources['_title_banner'] > plan.topic

Usage:
    set -a; source .env.local; set +a
    PYTHONPATH=. python3 scripts/render_v3_lee_han_4house.py \\
        data/political_pro/20260617_145717_lee_han_4house 0 \\
        --order "H,O1,T1,O2,T2,C"
"""
from __future__ import annotations

import argparse
import json as _json
import os
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

# V3 락인 (2026-06-16) — TTS 1.2배
TTS_SPEED = 1.2

# Charon voice config (V2 락인과 동일)
TTS_VOICE = "Charon"
TTS_TEMP = 0.5

# 다른 TTS 비트(T1/T2/CTA) 배경 offset — Hook 배경 영상에서 다른 컷 가져오기
TTS_EXTRA_OFFSETS = (10.0, 90.0, 120.0)


def _resolve(work_dir: Path, rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    return p if p.is_absolute() else (work_dir / rel_or_abs).resolve()


def _synthesize_tts_via_script(
    *, tts_texts: list[str], title: str, work_dir: Path,
) -> tuple[Path, list[dict]]:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise SystemExit("GEMINI_API_KEY 필요 (set -a; source .env.local; set +a)")

    scenes: list[Scene] = []
    cursor = 0.0
    for i, txt in enumerate(tts_texts):
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
        style_prompt=None,
        temperature=TTS_TEMP,
    )
    print(f"✅ TTS 합성: {audio_path.name}", file=sys.stderr)
    return audio_path, timings


def _split_subtitle_lines(subtitle: str) -> tuple[str, ...]:
    return tuple(s.strip() for s in subtitle.split("/") if s.strip())


def parse_order(order_str: str, plan: HybridShortsPlan) -> list[int]:
    all_beats = plan.all_beats()
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
                raise SystemExit(f"❌ {tok} — 원본 비트 {n}번 없음")
            result.append(orig_to_all_idx[n - 1])
        elif tok.startswith("T") and tok[1:].isdigit():
            n = int(tok[1:])
            if not (1 <= n <= len(tts_to_all_idx)):
                raise SystemExit(f"❌ {tok} — TTS 비트 {n}번 없음")
            result.append(tts_to_all_idx[n - 1])
        else:
            raise SystemExit(f"❌ 토큰 {tok!r} 알 수 없음")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description="V3 하이브리드 렌더 (Lee↔Han 4house 변형)",
    )
    ap.add_argument("plans_dir", type=Path)
    ap.add_argument("plan_idx", type=int, choices=[0, 1, 2])
    ap.add_argument("--order", type=str, default="H,O1,T1,O2,T2,C")
    args = ap.parse_args()
    out_dir = args.plans_dir.resolve()
    plan_idx = args.plan_idx

    plans_json = out_dir / "plans_hybrid.json"
    if not plans_json.exists():
        raise SystemExit(f"❌ plans_hybrid.json not found: {plans_json}")

    result = ThreeHybridPlansResult.from_dict(
        _json.loads(plans_json.read_text(encoding="utf-8"))
    )
    plan: HybridShortsPlan = result.plans[plan_idx]
    print(f"✅ Plan {plan_idx + 1} — angle={plan.angle}, "
          f"TTS={plan.tts_seconds:.1f}s, ORIG={plan.original_seconds:.1f}s",
          file=sys.stderr)

    ts = int(_time.time())
    work_dir = out_dir / f"v3_plan{plan_idx}_{ts}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 제목 띠
    title_text = (
        os.environ.get("TITLE_BANNER")
        or plan.extra_clip_sources.get("_title_banner")
        or plan.topic[:18]
    )
    title_png = work_dir / "title_banner.png"
    render_title_banner_png(text=title_text, out_path=title_png)
    print(f"📌 제목 띠: {title_text!r}", file=sys.stderr)

    # Hook 배경 영상 (이재명)
    hook_bg_rel = plan.extra_clip_sources.get("_hook_background_clip", "")
    if not hook_bg_rel:
        raise SystemExit("❌ plan.extra_clip_sources['_hook_background_clip'] 비어있음")
    hook_bg_clip = _resolve(out_dir, hook_bg_rel)
    hook_bg_offset = float(
        plan.extra_clip_sources.get("_hook_background_offset_sec", "0.0")
    )
    if not hook_bg_clip.exists():
        raise SystemExit(f"❌ Hook background clip 없음: {hook_bg_clip}")
    print(f"🎬 Hook 배경: {hook_bg_clip.name} @ {hook_bg_offset:.1f}s",
          file=sys.stderr)

    # 한성숙 배경 영상 (TTS 비트 후반부용) — 선택적
    han_bg_rel = plan.extra_clip_sources.get("_han_background_clip", "")
    han_bg_clip: Path | None = None
    han_bg_offsets: tuple[float, ...] = ()
    han_after_beat_idx: int | None = None
    if han_bg_rel:
        han_bg_clip = _resolve(out_dir, han_bg_rel)
        if not han_bg_clip.exists():
            raise SystemExit(f"❌ Han background clip 없음: {han_bg_clip}")
        offsets_str = plan.extra_clip_sources.get("_han_background_offsets", "0.0")
        han_bg_offsets = tuple(float(s) for s in offsets_str.split(",") if s.strip())
        han_after_beat_idx = int(plan.extra_clip_sources.get("_han_after_beat_idx", "999"))
        print(
            f"🎬 한성숙 배경: {han_bg_clip.name} @ {han_bg_offsets} "
            f"(beat_idx ≥ {han_after_beat_idx})",
            file=sys.stderr,
        )

    # 비트 순서
    all_beats = plan.all_beats()
    tts_beats: list[HybridBeat] = [b for b in all_beats if b.kind == "tts"]
    tts_texts = [b.tts_text for b in tts_beats]
    tts_beat_order = [i for i, b in enumerate(all_beats) if b.kind == "tts"]
    chunk_sequence = parse_order(args.order, plan)
    print(f"📐 비트 순서: {args.order!r} → {chunk_sequence}", file=sys.stderr)

    tts_mp3, timings = _synthesize_tts_via_script(
        tts_texts=tts_texts,
        title=f"{plan.topic[:25]}_plan{plan_idx + 1}",
        work_dir=work_dir,
    )

    timing_map = {t["scene_id"]: t for t in timings if t["scene_id"] != -1}
    tts_ranges: dict[int, tuple[float, float]] = {}
    for tts_idx_in_list, beat_idx in enumerate(tts_beat_order):
        t = timing_map.get(tts_idx_in_list)
        if t is None:
            raise SystemExit(f"TTS timing 누락 (scene_id={tts_idx_in_list})")
        tts_ranges[beat_idx] = (t["start_ms"] / 1000, t["end_ms"] / 1000)

    chunks: list[Path] = []
    tts_extra_idx = 0
    han_offset_idx = 0
    last_all_idx = len(all_beats) - 1

    for i, beat_idx in enumerate(chunk_sequence):
        beat = all_beats[beat_idx]
        chunk_out = work_dir / f"{i:02d}_{beat.kind}_b{beat_idx}.mp4"
        sub_png = work_dir / f"{i:02d}_sub.png"

        if beat.kind == "tts":
            lines = _split_subtitle_lines(beat.subtitle)
            is_hook = (beat_idx == 0)
            is_cta = (beat_idx == last_all_idx)
            render_subtitle_png(
                style=SubtitleStyle(
                    lines=lines,
                    color_name=beat.subtitle_color,
                    emphasis=beat.subtitle_emphasis or is_hook or is_cta,
                ),
                out_path=sub_png,
            )
            t_start, t_end = tts_ranges[beat_idx]

            # 배경 선택 분기:
            #   - Hook: 사용자 지정 hook offset
            #   - 한성숙 영상 지정 + beat_idx ≥ han_after_beat_idx: 한성숙 영상
            #   - 그 외 TTS 비트: 같은 이재명 영상의 다른 offset
            if is_hook:
                bg_clip = hook_bg_clip
                bg_off = hook_bg_offset
            elif (
                han_bg_clip is not None
                and han_after_beat_idx is not None
                and beat_idx >= han_after_beat_idx
                and han_bg_offsets
            ):
                bg_clip = han_bg_clip
                bg_off = han_bg_offsets[han_offset_idx % len(han_bg_offsets)]
                han_offset_idx += 1
            else:
                bg_clip = hook_bg_clip
                bg_off = TTS_EXTRA_OFFSETS[tts_extra_idx % len(TTS_EXTRA_OFFSETS)]
                tts_extra_idx += 1

            build_tts_beat(
                beat=beat,
                background_clip=bg_clip,
                background_offset_sec=bg_off,
                tts_audio_full=tts_mp3,
                tts_start_sec=t_start,
                tts_end_sec=t_end,
                subtitle_png=sub_png,
                out=chunk_out,
                title_banner_png=title_png,
                speed=TTS_SPEED,
            )
        else:  # original
            src_clip = _resolve(out_dir, beat.source_clip_path)
            if not src_clip.exists():
                raise SystemExit(f"❌ original 비트 소스 영상 없음: {src_clip}")
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
            build_original_beat(
                beat=beat,
                source_clip=src_clip,
                subtitle_png=sub_png,
                out=chunk_out,
                title_banner_png=title_png,
            )
        chunks.append(chunk_out)

    # Outro
    outro = work_dir / "99_outro.mp4"
    build_outro_from_image(
        image_path=ROOT / "public/outro.png",
        out=outro,
        duration=4.0,
        source_label=f"출처: {plan.source_channel} · {plan.source_title}",
    )
    chunks.append(outro)

    final = out_dir / f"V3_HYBRID_plan{plan_idx + 1}_{plan.angle}_{ts}.mp4"
    print(f"🎬 concat {len(chunks)}개 청크 → {final.name}", file=sys.stderr)
    concat_chunks(chunks, final)
    print(f"✅ FINAL: {final}", file=sys.stderr)
    print(str(final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
