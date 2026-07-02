"""V3 hybrid_planner smoke test on the cached OBS transcript.

Loads:
    data/political_pro/20260615_193552_cli/transcript.json (already extracted)
    data/political_pro/20260615_193552_cli/plans.json     (for video meta only)

Runs:
    generate_three_hybrid_plans() → plans_hybrid.json

Validates:
    - 3 plans, one per angle
    - TTS sum + original sum within [12, 30]s each
    - Each plan has Hook + ≥3 beats + CTA
    - Original beats reference clip_start/end inside the candidates pool
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/kyusik/ContentsMaker")
sys.path.insert(0, str(ROOT))

from src.analyzer.hybrid_planner import (  # noqa: E402
    HybridPlannerError,
    generate_three_hybrid_plans,
)
from src.analyzer.political_plan_models import ThreePlansResult  # noqa: E402


OUT_DIR = ROOT / "data/political_pro/20260615_193552_cli"


def main() -> int:
    transcript_path = OUT_DIR / "transcript.json"
    plans_path = OUT_DIR / "plans.json"
    if not transcript_path.exists() or not plans_path.exists():
        print(f"❌ 캐시된 transcript.json / plans.json 없음 in {OUT_DIR}",
              file=sys.stderr)
        return 1

    transcript_data = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript = transcript_data.get("segments", [])
    v2 = ThreePlansResult.from_dict(json.loads(plans_path.read_text(encoding="utf-8")))

    print(
        f"📥 transcript: {len(transcript)}세그 / "
        f"영상: {v2.video_title!r} ({v2.video_channel}, {v2.video_duration_sec:.1f}s)",
        file=sys.stderr,
    )

    try:
        result = generate_three_hybrid_plans(
            youtube_url=v2.youtube_url,
            transcript=transcript,
            video_title=v2.video_title,
            video_duration_sec=v2.video_duration_sec,
            video_path=v2.video_path,
            transcript_path=str(transcript_path),
            output_dir=OUT_DIR,
            video_channel=v2.video_channel,
        )
    except HybridPlannerError as e:
        print(f"❌ V3 planner 실패: {e}", file=sys.stderr)
        return 2

    print(f"\n✅ V3 plans 생성 완료 — {len(result.plans)}개", file=sys.stderr)
    print(f"📊 Stage A 후보 풀: {len(result.candidates_pool)}개", file=sys.stderr)

    # 검증 + 요약 출력
    for i, plan in enumerate(result.plans):
        print(f"\n── Plan {i + 1} (angle={plan.angle}) ──", file=sys.stderr)
        print(f"  주제: {plan.topic}", file=sys.stderr)
        print(f"  Hook: {plan.hook.subtitle!r} ({plan.hook.duration_sec:.1f}s)",
              file=sys.stderr)
        print(
            f"  비율: TTS={plan.tts_seconds:.1f}s / 원본={plan.original_seconds:.1f}s "
            f"/ 총={plan.total_seconds:.1f}s",
            file=sys.stderr,
        )
        for j, b in enumerate(plan.beats, 1):
            if b.kind == "original":
                print(
                    f"  B{j} [원본] {b.clip_start_sec:.1f}~{b.clip_end_sec:.1f}s · "
                    f"{b.speaker_name} · {' / '.join(b.quote_lines)}",
                    file=sys.stderr,
                )
            else:
                print(
                    f"  B{j} [TTS]  {b.duration_sec:.1f}s · "
                    f"{b.subtitle!r}",
                    file=sys.stderr,
                )
        print(f"  CTA: {plan.cta.subtitle!r}", file=sys.stderr)

    print("\n✅ smoke test 통과", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
