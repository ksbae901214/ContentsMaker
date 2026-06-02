"""Phase 8 Polish CLI 핸들러 — cli.py 800줄 한계(원칙 5) 준수를 위해 분리.

본 모듈은 4개 배치 명령의 인자 처리·로깅·예외 정규화만 담당. 비즈니스 로직은
모두 `src/dem_shorts/{metrics_updater,archive_rotator,e2e_smoke}` 와
`src/dem_shorts/compliance/guardrail_learner` 에 위치.

cli.py 의 build_parser() 가 본 모듈의 함수를 set_defaults(func=...) 에 바인딩.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH, ensure_dirs


def cmd_metrics_update(args: argparse.Namespace) -> int:
    """T118: YouTube 메트릭 갱신 배치 (B-05).

    cron: `0 * * * *` (1시간 주기). 업로드 후 24h fresh window 는 운영에서
    별도 cron(15분)으로 동일 명령을 더 자주 실행한다.
    """
    from src.dem_shorts.metrics_updater import update_metrics
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    log_event("metrics-update", "started", limit=args.limit, dry_run=args.dry_run)
    try:
        with get_connection(DB_PATH) as conn:
            summary = update_metrics(conn, limit=args.limit, dry_run=args.dry_run)
    except Exception as exc:
        log_event("metrics-update", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    log_event("metrics-update", "done", **summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_archive_rotate(args: argparse.Namespace) -> int:
    """T119: 아카이브 순환 배치 (B-06).

    cron: `0 3 * * 6` (매주 토 03:00). `--days` 이상된 source_videos 의
    download_path 파일을 콜드 스토리지로 이동.
    """
    from src.dem_shorts.archive_rotator import rotate_archive
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    log_event(
        "archive-rotate", "started",
        days=args.days, cold_dir=args.cold_dir, dry_run=args.dry_run,
    )
    try:
        with get_connection(DB_PATH) as conn:
            summary = rotate_archive(
                conn,
                days=args.days,
                cold_dir=args.cold_dir,
                dry_run=args.dry_run,
            )
    except Exception as exc:
        log_event("archive-rotate", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    log_event("archive-rotate", "done", **summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_guardrail_learn(args: argparse.Namespace) -> int:
    """T120: 가드레일 키워드 가중치 재학습 (B-08, FR-028).

    cron: `0 3 1 * *` (매월 1일 03:00). guardrail_history 의 운영자
    수정·무시 이력을 분석해 keyword_multipliers JSON 산출.
    """
    from src.dem_shorts.compliance.guardrail_learner import run_learning
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    log_event(
        "guardrail-learn", "started",
        days=args.days, out=args.out, dry_run=args.dry_run,
    )
    try:
        with get_connection(DB_PATH) as conn:
            summary = run_learning(
                conn,
                out_path=args.out,
                days=args.days,
                dry_run=args.dry_run,
            )
    except Exception as exc:
        log_event("guardrail-learn", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    log_event("guardrail-learn", "done", **summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_test_e2e(args: argparse.Namespace) -> int:
    """T123: 엔드투엔드 스모크 실행 (R-15).

    기본 stub 모드는 ~1초 — CI 가드. `--real-models` 는 실제 Whisper/pyannote/
    Remotion 호출 (5~10분, 샘플 mp4 필수).
    """
    from src.dem_shorts.e2e_smoke import run_e2e_smoke
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    sample = Path(args.sample) if args.sample else Path("tests/fixtures/natv_sample.mp4")
    log_event(
        "test-e2e", "started",
        sample=str(sample), real_models=args.real_models, video_id=args.video_id,
    )
    try:
        result = run_e2e_smoke(
            sample_path=sample,
            db_path=DB_PATH,
            real_models=args.real_models,
            operator_id=args.operator_id,
            video_id=args.video_id,
        )
    except Exception as exc:
        log_event("test-e2e", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    log_event(
        "test-e2e", "done",
        rendered=result["phases"]["render"]["rendered_path"],
        duration_sec=result["phases"]["render"]["duration_sec"],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
