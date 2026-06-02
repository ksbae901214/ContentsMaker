"""SC-003 발언자 식별 정확도 측정 (T130).

사용 절차:
    # 1. NATV 영상 10편 다운로드 + STT/diarize/identify 실행
    for VID in v1 v2 ...; do
        python3 -m src.dem_shorts.cli download --video-id "$VID"
        python3 -m src.dem_shorts.cli stt --video-id "$VID"
        python3 -m src.dem_shorts.cli diarize --video-id "$VID"
        python3 -m src.dem_shorts.cli identify --video-id "$VID"
    done

    # 2. tests/fixtures/sc003_ground_truth.example.json 을 복사 후 라벨링
    cp tests/fixtures/sc003_ground_truth.example.json \
       tests/fixtures/sc003_ground_truth.json
    # → 운영자가 직접 청취하면서 turns 작성

    # 3. 정확도 측정
    python3 scripts/dem_shorts/measure_sc003.py
    python3 scripts/dem_shorts/measure_sc003.py --json sc003.json

Exit code:
    0 = SC-003 통과 (정확도 ≥ 0.80)
    1 = 미통과 또는 ground-truth 없음
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.dem_shorts.db import get_connection  # noqa: E402
from src.dem_shorts.sc003_comparator import (  # noqa: E402
    compute_accuracy,
    load_ground_truth,
)
from src.dem_shorts.utils.paths import DB_PATH  # noqa: E402

DEFAULT_GT = ROOT / "tests" / "fixtures" / "sc003_ground_truth.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="SC-003 발언자 식별 정확도 측정 (T130)")
    parser.add_argument(
        "--ground-truth",
        default=str(DEFAULT_GT),
        help=f"라벨 파일 경로 (default {DEFAULT_GT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        help=f"SQLite 경로 (default {DB_PATH})",
    )
    parser.add_argument("--json", default=None, help="결과 JSON 저장 경로")
    args = parser.parse_args()

    gt_path = Path(args.ground_truth)
    if not gt_path.exists():
        print(
            f"ERROR: {gt_path} 없음.\n"
            f"tests/fixtures/sc003_ground_truth.example.json 을 복사 후 "
            f"라벨링하세요.",
            file=sys.stderr,
        )
        return 1

    gt = load_ground_truth(gt_path)
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: SQLite DB not found: {db_path}", file=sys.stderr)
        return 1

    with get_connection(db_path) as conn:
        result = compute_accuracy(conn, gt)

    if result["total_turns"] == 0:
        print(
            "WARN: ground-truth 에 측정 가능한 turn 이 없습니다.\n"
            "video_id 가 EXAMPLE_ 로 시작하는 항목은 자동 제외됩니다.\n"
            "실제 NATV video_id 로 작성하세요.",
            file=sys.stderr,
        )

    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        Path(args.json).write_text(out, encoding="utf-8")
        print(f"[SC-003] saved to {args.json}", file=sys.stderr)
    print(out)

    return 0 if result["sc_003_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
