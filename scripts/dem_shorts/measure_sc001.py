"""SC-001 measurement harness — 30분 이내 end-to-end 검증 (T129).

사용법:
    # 사전: tests/fixtures/natv_sample.mp4 배치 (또는 NATV_SMOKE_SAMPLE 환경변수)
    python3 scripts/dem_shorts/measure_sc001.py
    python3 scripts/dem_shorts/measure_sc001.py --sample /path/to/your.mp4
    python3 scripts/dem_shorts/measure_sc001.py --json out.json

운영자 30분 SC 의 자동 측정 부분(STT/diarize/identify/score/draft/gate/render)만
계측한다. 운영자 수동 단계(해설 작성·팩트 URL 첨부 등)는 별도 스톱워치로 측정.

본 스크립트는 `e2e_smoke.run_e2e_smoke(real_models=True)` 를 호출하므로 실제
Whisper large-v3 + pyannote 3.1 + Remotion 이 실행된다 (5~10분 소요).

출력 형식:
    {
      "sample_path": "...",
      "wall_clock_sec": 612.4,
      "auto_pipeline_budget_sec": 900,    # 15분 (운영자 해설용 15분 여유)
      "sc_001_auto_pass": true,           # 15분 이내 완료
      "phases": {
        "stt": {"elapsed_sec": 145.3, ...},
        ...
      }
    }
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dem_shorts.db import init_db  # noqa: E402
from src.dem_shorts.e2e_smoke import run_e2e_smoke  # noqa: E402

# 자동 단계는 30분 중 절반(15분) 안에 완료 — 운영자 해설/검수 15분 여유
AUTO_BUDGET_SEC = 900


def _resolve_sample(arg: str | None) -> Path:
    if arg:
        p = Path(arg)
        if not p.exists():
            print(f"ERROR: sample not found at {p}", file=sys.stderr)
            sys.exit(2)
        return p
    env = os.getenv("NATV_SMOKE_SAMPLE")
    if env:
        p = Path(env)
        if not p.exists():
            print(f"ERROR: NATV_SMOKE_SAMPLE not found at {p}", file=sys.stderr)
            sys.exit(2)
        return p
    default = ROOT / "tests" / "fixtures" / "natv_sample.mp4"
    if not default.exists():
        print(
            "ERROR: tests/fixtures/natv_sample.mp4 미배치.\n"
            "tests/fixtures/README.md 참조하여 NATV 영상 1편을 10분 trim 후 "
            "해당 경로에 배치하거나 --sample <PATH> 인자 또는 "
            "NATV_SMOKE_SAMPLE 환경변수를 사용하세요.",
            file=sys.stderr,
        )
        sys.exit(2)
    return default


def main() -> int:
    parser = argparse.ArgumentParser(description="SC-001 30분 이내 end-to-end 측정 (T129)")
    parser.add_argument("--sample", default=None, help="NATV mp4 경로 (default tests/fixtures/natv_sample.mp4)")
    parser.add_argument("--json", default=None, help="JSON 결과 저장 경로 (생략 시 stdout)")
    parser.add_argument("--video-id", default="sc001_check")
    parser.add_argument("--operator-id", default="sc001-bench")
    args = parser.parse_args()

    sample = _resolve_sample(args.sample)

    # 격리 DB 사용 (운영 DB 오염 방지)
    with tempfile.TemporaryDirectory(prefix="sc001_") as tmp:
        db_path = Path(tmp) / "bench.db"
        init_db(db_path)

        print(f"[SC-001] sample={sample}", file=sys.stderr)
        print(f"[SC-001] real_models=True (Whisper + pyannote + Remotion 호출)", file=sys.stderr)
        print(f"[SC-001] 예상 소요 5~10분 ...", file=sys.stderr)
        t0 = time.perf_counter()
        try:
            result = run_e2e_smoke(
                sample_path=sample,
                db_path=db_path,
                real_models=True,
                operator_id=args.operator_id,
                video_id=args.video_id,
            )
        except Exception as exc:
            print(f"ERROR: pipeline failed — {exc}", file=sys.stderr)
            return 1
        wall = round(time.perf_counter() - t0, 3)

    auto_pass = wall <= AUTO_BUDGET_SEC
    payload = {
        "sample_path": str(sample),
        "wall_clock_sec": wall,
        "auto_pipeline_budget_sec": AUTO_BUDGET_SEC,
        "sc_001_auto_pass": auto_pass,
        "operator_manual_budget_sec": 1800 - AUTO_BUDGET_SEC,
        "note": (
            "auto_pass=True 이면 SC-001 30분 중 자동 단계 절반(15분) 충족. "
            "나머지 15분은 운영자 해설·게이트 수동 검수에 배정."
        ),
        "phases": result.get("phases", {}),
        "phases_total_elapsed_sec": result.get("total_elapsed_sec"),
    }

    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(out, encoding="utf-8")
        print(f"[SC-001] saved to {args.json}", file=sys.stderr)
    print(out)

    return 0 if auto_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
