"""Dem-Shorts Studio CLI — 배치·개발자 디버깅 진입점.

Usage:
    python3 -m src.dem_shorts.cli <subcommand> [flags]

서브커맨드는 contracts/cli-commands.md 참조.
MVP 단계에서는 `db-init` 만 구현되어 있으며, 나머지는 후속 태스크에서 추가.
"""
from __future__ import annotations

import argparse
import json
import sys

from src.dem_shorts import cli_polish as _polish
from src.dem_shorts.db import get_connection, init_db
from src.dem_shorts.utils.paths import DB_PATH, ensure_dirs


def _cmd_db_init(args: argparse.Namespace) -> int:
    """T020: DB 마이그레이션 + seed 실행."""
    ensure_dirs()
    result = init_db(DB_PATH)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_poll_natv(args: argparse.Namespace) -> int:
    """T031: NATV 채널 폴링 + source_videos upsert."""
    from src.dem_shorts.source_collector import poll_natv
    from src.dem_shorts.utils.logger import log_event
    from src.dem_shorts.youtube_client import YoutubeApiError, YoutubeQuotaExceeded

    ensure_dirs()
    log_event("poll-natv", "started", since_hours=args.since_hours, dry_run=args.dry_run)
    try:
        with get_connection(DB_PATH) as conn:
            records = poll_natv(
                conn, since_hours=args.since_hours, dry_run=args.dry_run
            )
    except YoutubeQuotaExceeded as exc:
        log_event("poll-natv", "failed", error="quota_exceeded", detail=str(exc)[:200])
        print(json.dumps({"error": "quota_exceeded", "detail": str(exc)}, ensure_ascii=False))
        return 2
    except YoutubeApiError as exc:
        log_event("poll-natv", "failed", error="api_error", detail=str(exc)[:200])
        print(json.dumps({"error": "api_error", "detail": str(exc)}, ensure_ascii=False))
        return 1

    for rec in records:
        print(
            json.dumps(
                {
                    "event": "excluded" if rec["excluded_reason"] else "new",
                    "video_id": rec["video_id"],
                    "title": rec["title"],
                    "duration_sec": rec["duration_sec"],
                    "excluded_reason": rec["excluded_reason"],
                },
                ensure_ascii=False,
            )
        )
    log_event("poll-natv", "done", new_count=len(records))
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    """T032: 단일 영상 yt-dlp 다운로드."""
    from src.dem_shorts.source_collector import DownloadError, download_video
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    log_event("download", "started", video_id=args.video_id)
    try:
        path = download_video(args.video_id)
    except DownloadError as exc:
        log_event("download", "failed", video_id=args.video_id, detail=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    log_event("download", "done", video_id=args.video_id, path=str(path))
    print(json.dumps({"video_id": args.video_id, "path": str(path)}, ensure_ascii=False))
    return 0


def _cmd_stt(args: argparse.Namespace) -> int:
    """T052: Whisper STT 실행."""
    from pathlib import Path

    from src.dem_shorts.stt import STTError, transcribe_video
    from src.dem_shorts.utils.logger import log_event
    from src.dem_shorts.utils.paths import archive_path

    ensure_dirs()
    video_path = Path(args.video_path) if args.video_path else archive_path(args.video_id)
    log_event("stt", "started", video_id=args.video_id)
    try:
        out = transcribe_video(
            video_path,
            video_id=args.video_id,
            model_name=args.model,
            device=args.device,
        )
    except STTError as exc:
        log_event("stt", "failed", video_id=args.video_id, detail=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    log_event("stt", "done", video_id=args.video_id, path=str(out))
    print(json.dumps({"video_id": args.video_id, "transcript_path": str(out)}, ensure_ascii=False))
    return 0


def _cmd_diarize(args: argparse.Namespace) -> int:
    """T052: pyannote 화자 분리."""
    from pathlib import Path

    from src.dem_shorts.diarization import DiarizationError, diarize_video
    from src.dem_shorts.utils.logger import log_event
    from src.dem_shorts.utils.paths import archive_path

    ensure_dirs()
    video_path = Path(args.video_path) if args.video_path else archive_path(args.video_id)
    log_event("diarize", "started", video_id=args.video_id)
    try:
        out = diarize_video(video_path, video_id=args.video_id)
    except DiarizationError as exc:
        log_event("diarize", "failed", video_id=args.video_id, detail=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    log_event("diarize", "done", video_id=args.video_id, path=str(out))
    print(json.dumps({"video_id": args.video_id, "segments_path": str(out)}, ensure_ascii=False))
    return 0


def _cmd_identify(args: argparse.Namespace) -> int:
    """T052: 발언자 식별 → speech_segments upsert."""
    from src.dem_shorts.speaker_id.identify import identify_speakers
    from src.dem_shorts.utils.logger import log_event

    log_event("identify", "started", video_id=args.video_id)
    try:
        with get_connection(DB_PATH) as conn:
            saved = identify_speakers(conn, args.video_id)
    except Exception as exc:
        log_event("identify", "failed", video_id=args.video_id, detail=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    log_event("identify", "done", video_id=args.video_id, saved=saved)
    print(json.dumps({"video_id": args.video_id, "saved_segments": saved}))
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    """T033: 지정 영상의 dem_score 재계산.

    MVP 단계에서는 SpeechSegment 데이터가 아직 없으므로 기본 집계만 수행.
    발언자 식별(Phase 4) 완료 후 본 명령이 본격 활용됨.
    """
    from src.dem_shorts.scoring import DemScoreInputs, calculate_dem_score

    with get_connection(DB_PATH) as conn:
        row = conn.execute(
            "SELECT duration_sec FROM source_videos WHERE video_id = ?",
            (args.video_id,),
        ).fetchone()
        if not row:
            print(json.dumps({"error": "video not found"}), file=sys.stderr)
            return 1

        # Phase 4 발언자 식별이 없으면 모두 0. 본격 계산은 T049 이후.
        inputs = DemScoreInputs(
            dem_person_count=0,
            has_top_whitelist=False,
            top3_present={"이재명": False, "조국": False, "정청래": False},
            female_or_youth_present=False,
            issue_keyword_matches=0,
            duration_sec=int(row[0]),
            recent_repeat_count=0,
        )
        score = calculate_dem_score(inputs)
        conn.execute(
            "UPDATE source_videos SET dem_score = ?, updated_at = datetime('now') WHERE video_id = ?",
            (score, args.video_id),
        )
        conn.commit()
    print(json.dumps({"video_id": args.video_id, "dem_score": score}))
    return 0


def _cmd_draft_create(args: argparse.Namespace) -> int:
    """T095: draft 생성."""
    from src.dem_shorts.drafts_repo import DraftError, create_draft

    with get_connection(DB_PATH) as conn:
        try:
            draft = create_draft(conn, {
                "segment_id": args.segment_id,
                "cut_start_sec": args.cut_start,
                "cut_end_sec": args.cut_end,
                "subtitle_preset": args.preset,
            })
        except DraftError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return 1
    print(json.dumps({"draft": draft}, ensure_ascii=False, default=str, indent=2))
    return 0


def _cmd_commentary(args: argparse.Namespace) -> int:
    """T095: AI 해설 후보 3개 생성."""
    from src.dem_shorts.compliance.election_guard import is_in_election_period
    from src.dem_shorts.editor.commentary_gen import (
        CommentaryContext,
        CommentaryGenError,
        generate_commentary_candidates,
    )

    with get_connection(DB_PATH) as conn:
        draft = conn.execute(
            "SELECT * FROM shorts_drafts WHERE id=?", (args.draft_id,)
        ).fetchone()
        if not draft:
            print(json.dumps({"error": "draft_not_found"}), file=sys.stderr)
            return 1
        segment = conn.execute(
            "SELECT * FROM speech_segments WHERE id=?", (draft["segment_id"],)
        ).fetchone()
        politician = None
        if segment and segment["politician_id"]:
            politician = conn.execute(
                "SELECT * FROM politicians WHERE id=?", (segment["politician_id"],)
            ).fetchone()
        sv = conn.execute(
            "SELECT session_type FROM source_videos WHERE video_id=?",
            (segment["source_video_id"],),
        ).fetchone() if segment else None

    ctx = CommentaryContext(
        politician_name=politician["name"] if politician else "(미식별)",
        stt_text=segment["stt_text"] if segment else "",
        tone_guide=politician["tone_guide"] if politician else "",
        tone_hint=args.tone,
        session_type=sv["session_type"] if sv else "",
        is_election_period=is_in_election_period(),
    )
    try:
        candidates = generate_commentary_candidates(ctx)
    except CommentaryGenError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2))
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    """T095: 컴플라이언스 게이트 실행. Exit 0=pass, 1=fail, 2=warn_only."""
    from src.dem_shorts.compliance.gate import GateContext, GateError, validate

    signed_fact = args.operator_id if args.manual_fact_check else None
    signed_def = args.operator_id if args.manual_defamation_check else None
    ctx = GateContext(
        draft_id=args.draft_id,
        manual_fact_check_signed_by=signed_fact,
        manual_defamation_check_signed_by=signed_def,
        operator_id=args.operator_id,
    )
    try:
        result = validate(ctx)
    except GateError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    out = result.to_dict()
    out["is_passed"] = result.is_passed()
    print(json.dumps(out, ensure_ascii=False, indent=2))

    if result.is_passed():
        return 0
    if result.overall_status == "warn_only":
        return 2
    return 1


def _cmd_render(args: argparse.Namespace) -> int:
    """T095: 렌더링."""
    from src.dem_shorts.renderer import RenderError, render_draft

    try:
        result = render_draft(args.draft_id, skip_remotion=args.skip_remotion)
    except RenderError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "rendered_path": str(result.rendered_path),
        "duration_sec": result.duration_sec,
        "used_cache": result.used_cache,
        "cache_key": result.cache_key,
    }, ensure_ascii=False, indent=2))
    return 0


def _cmd_upload(args: argparse.Namespace) -> int:
    """T095: YouTube 업로드."""
    from datetime import datetime
    from pathlib import Path

    from src.dem_shorts.uploader import UploadError, UploadRequest, upload

    desc = Path(args.description_file).read_text(encoding="utf-8")
    tags = tuple(t.strip() for t in args.tags.split(",") if t.strip())
    sched = None
    if args.schedule:
        try:
            sched = datetime.fromisoformat(args.schedule.replace("Z", "+00:00"))
        except ValueError:
            print(json.dumps({"error": "invalid_schedule_format"}))
            return 1

    req = UploadRequest(
        draft_id=args.draft_id,
        title=args.title,
        description=desc,
        tags=tags,
        scheduled_publish_at=sched,
        operator_confirmed=True,
    )
    try:
        result = upload(req, dry_run=args.dry_run)
    except UploadError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "youtube_video_id": result.youtube_video_id,
        "youtube_url": result.youtube_url,
    }, ensure_ascii=False, indent=2))
    return 0


def _cmd_bgm_register(args: argparse.Namespace) -> int:
    """T095: BGM manifest 등록."""
    from pathlib import Path

    from src.dem_shorts.editor.bgm_manifest import BgmManifestError, register_bgm
    from src.dem_shorts.utils.paths import BGM_MANIFEST

    try:
        register_bgm(
            BGM_MANIFEST,
            filename=args.filename,
            mood=args.mood,
            license_text=args.license_text,
            audio_path=Path(args.path),
        )
    except BgmManifestError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"registered": args.filename}, ensure_ascii=False))
    return 0


def _cmd_election_check(args: argparse.Namespace) -> int:
    """T102: 선거기간 감지 배치 (B-07).

    매일 00:01 cron (`1 0 * * *`)에서 호출. FR-030 D-180/D-120 경계 진입 시
    운영자 알림용 로그 + 중립 모드 플래그를 반환한다. 하드코딩 테이블만
    조회하므로 1초 미만 실행.

    Exit codes:
        0: 조회 성공 (선거기간 여부 무관)
        1: 예외 발생
    """
    from src.dem_shorts.compliance.election_guard import (
        get_bias_threshold,
        get_election_status,
    )
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    try:
        result = get_election_status()
    except Exception as exc:  # defensive — 하드코딩 테이블이라 드문 케이스
        log_event("election-check", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    payload = {
        "in_election_period": result.in_election_period,
        "next_election_type": result.next_election_type,
        "next_election_date": (
            result.next_election_date.isoformat()
            if result.next_election_date
            else None
        ),
        "days_until": result.days_until,
        "guard_threshold_days": result.guard_threshold_days,
        "bias_threshold": get_bias_threshold(),
        "neutral_mode_enforced": result.in_election_period,
    }
    log_event("election-check", "done", **payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _cmd_ranking_batch(args: argparse.Namespace) -> int:
    """T111: 주간 여성·청년 랭킹 배치 (B-03, FR-008).

    cron: `0 22 * * 0` (매주 일요일 22:00 KST).
    """
    from datetime import date

    from src.dem_shorts.ranking_batch import resolve_week_start, run_ranking_batch
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    week_start = (
        date.fromisoformat(args.week_start) if args.week_start else resolve_week_start()
    )
    log_event("ranking-batch", "started", week_start=week_start.isoformat(), dry_run=args.dry_run)
    try:
        with get_connection(DB_PATH) as conn:
            result = run_ranking_batch(
                conn, week_start=week_start, dry_run=args.dry_run
            )
    except Exception as exc:
        log_event("ranking-batch", "failed", error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    log_event("ranking-batch", "done", **result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_bias_report(args: argparse.Namespace) -> int:
    """T113: 월간 편향 리포트 배치 (B-04, FR-038).

    cron: `0 9 1 * *` (매월 1일 09:00 KST).
    --month 생략 시 지난 달 자동 선택.
    """
    from datetime import date

    from src.dem_shorts.bias_report import (
        generate_bias_report,
        resolve_previous_month,
    )
    from src.dem_shorts.utils.logger import log_event

    ensure_dirs()
    if args.month:
        # YYYY-MM 또는 YYYY-MM-DD 수용
        try:
            parts = args.month.split("-")
            if len(parts) == 2:
                month = date(int(parts[0]), int(parts[1]), 1)
            else:
                month = date.fromisoformat(args.month).replace(day=1)
        except ValueError:
            print(json.dumps({"error": "invalid_month_format"}))
            return 1
    else:
        month = resolve_previous_month()

    log_event("bias-report", "started", month=month.isoformat())
    try:
        with get_connection(DB_PATH) as conn:
            report = generate_bias_report(conn, month=month, persist=not args.dry_run)
    except Exception as exc:
        log_event("bias-report", "failed", month=month.isoformat(), error=str(exc)[:200])
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1

    payload = report.to_dict()
    log_event(
        "bias-report",
        "done",
        month=month.isoformat(),
        total_uploads=report.total_uploads,
        warnings=len(report.recommendations),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_stub(name: str):
    """Not-yet-implemented placeholder for subcommands from later phases."""
    def _handler(_args: argparse.Namespace) -> int:
        print(
            f"[dem-shorts] '{name}' subcommand is not yet implemented. "
            f"See specs/007-dem-shorts-studio/tasks.md for the task that adds it.",
            file=sys.stderr,
        )
        return 2
    return _handler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.dem_shorts.cli",
        description="Dem-Shorts Studio — 민주당 친화형 정치 쇼츠 반자동 제작 (007)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # db-init (implemented — T020)
    p_init = subparsers.add_parser("db-init", help="SQLite 마이그레이션 + seed 실행")
    p_init.set_defaults(func=_cmd_db_init)

    # poll-natv (T031)
    p_poll = subparsers.add_parser("poll-natv", help="NATV 채널 신규 영상 폴링")
    p_poll.add_argument("--since-hours", type=int, default=24)
    p_poll.add_argument("--dry-run", action="store_true")
    p_poll.set_defaults(func=_cmd_poll_natv)

    # download (T032)
    p_dl = subparsers.add_parser("download", help="단일 영상 yt-dlp 다운로드")
    p_dl.add_argument("--video-id", required=True)
    p_dl.set_defaults(func=_cmd_download)

    # score (T033 — MVP stub; 실제 집계는 Phase 4 이후)
    p_sc = subparsers.add_parser("score", help="단일 영상 dem_score 재계산")
    p_sc.add_argument("--video-id", required=True)
    p_sc.set_defaults(func=_cmd_score)

    # stt (T052)
    p_stt = subparsers.add_parser("stt", help="Whisper로 영상 전사")
    p_stt.add_argument("--video-id", required=True)
    p_stt.add_argument("--video-path", default=None)
    p_stt.add_argument("--model", default="large-v3")
    p_stt.add_argument("--device", default=None)
    p_stt.set_defaults(func=_cmd_stt)

    # diarize (T052)
    p_di = subparsers.add_parser("diarize", help="pyannote 화자 분리")
    p_di.add_argument("--video-id", required=True)
    p_di.add_argument("--video-path", default=None)
    p_di.set_defaults(func=_cmd_diarize)

    # identify (T052)
    p_id = subparsers.add_parser("identify", help="발언자 식별 → speech_segments")
    p_id.add_argument("--video-id", required=True)
    p_id.set_defaults(func=_cmd_identify)

    # T095: draft-create, commentary, gate, render, upload 서브커맨드
    p_draft = subparsers.add_parser("draft-create", help="쇼츠 초안 생성")
    p_draft.add_argument("--segment-id", type=int, required=True)
    p_draft.add_argument("--cut-start", type=float, required=True)
    p_draft.add_argument("--cut-end", type=float, required=True)
    p_draft.add_argument("--preset", default="default")
    p_draft.set_defaults(func=_cmd_draft_create)

    p_comm = subparsers.add_parser("commentary", help="AI 해설 후보 3개 생성")
    p_comm.add_argument("--draft-id", type=int, required=True)
    p_comm.add_argument("--tone", default="팩트 기반 객관적")
    p_comm.set_defaults(func=_cmd_commentary)

    p_gate = subparsers.add_parser("gate", help="컴플라이언스 게이트 실행")
    p_gate.add_argument("--draft-id", type=int, required=True)
    p_gate.add_argument("--manual-fact-check", action="store_true")
    p_gate.add_argument("--manual-defamation-check", action="store_true")
    p_gate.add_argument("--operator-id", default="owner")
    p_gate.set_defaults(func=_cmd_gate)

    p_ren = subparsers.add_parser("render", help="쇼츠 렌더링 (게이트 통과 필요)")
    p_ren.add_argument("--draft-id", type=int, required=True)
    p_ren.add_argument("--skip-remotion", action="store_true", help="테스트용 dry run")
    p_ren.set_defaults(func=_cmd_render)

    p_up = subparsers.add_parser("upload", help="YouTube 업로드")
    p_up.add_argument("--draft-id", type=int, required=True)
    p_up.add_argument("--title", required=True)
    p_up.add_argument("--description-file", required=True, help="설명 텍스트 파일 경로")
    p_up.add_argument("--tags", default="", help="쉼표 구분")
    p_up.add_argument("--schedule", default=None, help="ISO 8601 예약 시각")
    p_up.add_argument("--dry-run", action="store_true")
    p_up.set_defaults(func=_cmd_upload)

    p_bgm = subparsers.add_parser("bgm-register", help="BGM 파일을 manifest에 등록")
    p_bgm.add_argument("--filename", required=True)
    p_bgm.add_argument("--mood", required=True)
    p_bgm.add_argument("--license", required=True, dest="license_text")
    p_bgm.add_argument("--path", required=True, help="실제 mp3 파일 경로")
    p_bgm.set_defaults(func=_cmd_bgm_register)

    # election-check (T102, B-07): 매일 00:01 cron (`1 0 * * *`)
    p_elec = subparsers.add_parser(
        "election-check",
        help="선거기간 감지 배치 — D-180/D-120 경계 체크",
    )
    p_elec.set_defaults(func=_cmd_election_check)

    # test-e2e (T123): 운영자 스모크 (수집~렌더 1회)
    p_te = subparsers.add_parser(
        "test-e2e",
        help="엔드투엔드 스모크 (stub 기본, --real-models 시 실제 모델 호출)",
    )
    p_te.add_argument(
        "--sample",
        default=None,
        help="샘플 NATV mp4 경로 (기본 tests/fixtures/natv_sample.mp4)",
    )
    p_te.add_argument(
        "--real-models",
        action="store_true",
        help="Whisper/pyannote/Remotion 을 실제로 호출 (5~10분 소요)",
    )
    p_te.add_argument("--operator-id", default="smoke")
    p_te.add_argument("--video-id", default="smoke_natv_001")
    p_te.set_defaults(func=_polish.cmd_test_e2e)

    # guardrail-learn (T120, B-08): 매월 1일 03:00 cron (`0 3 1 * *`)
    p_gl = subparsers.add_parser(
        "guardrail-learn",
        help="가드레일 이력 기반 키워드 가중치 재학습 (FR-028)",
    )
    p_gl.add_argument("--days", type=int, default=30, help="분석 기간 (default 30일)")
    p_gl.add_argument(
        "--out",
        default=None,
        help="가중치 JSON 출력 경로. 기본 data/dem_shorts/guardrail_weights.json",
    )
    p_gl.add_argument("--dry-run", action="store_true")
    p_gl.set_defaults(func=_polish.cmd_guardrail_learn)

    # archive-rotate (T119, B-06): 매주 토 03:00 cron (`0 3 * * 6`)
    p_ar = subparsers.add_parser(
        "archive-rotate",
        help="3개월 이상 원본 영상을 콜드 스토리지로 이동",
    )
    p_ar.add_argument("--days", type=int, default=90, help="이동 기준 경과일 (default 90)")
    p_ar.add_argument(
        "--cold-dir",
        default=None,
        help="콜드 디렉토리. 기본값은 $DEM_SHORTS_COLD_DIR 또는 data/dem_shorts/cold/",
    )
    p_ar.add_argument("--dry-run", action="store_true")
    p_ar.set_defaults(func=_polish.cmd_archive_rotate)

    # metrics-update (T118, B-05): 매시 cron (`0 * * * *`)
    p_mu = subparsers.add_parser(
        "metrics-update",
        help="업로드 쇼츠의 view/like/comment 갱신 (FR-038 입력)",
    )
    p_mu.add_argument(
        "--limit", type=int, default=30, help="1회 배치에서 갱신할 최대 업로드 수 (default 30)"
    )
    p_mu.add_argument("--dry-run", action="store_true")
    p_mu.set_defaults(func=_polish.cmd_metrics_update)

    # ranking-batch (T111, B-03): 매주 일 22:00 cron (`0 22 * * 0`)
    p_rb = subparsers.add_parser(
        "ranking-batch",
        help="주간 여성·청년 정치인 랭킹 갱신 (FR-008, FR-009)",
    )
    p_rb.add_argument("--week-start", default=None, help="YYYY-MM-DD (월요일). 기본=이번 주")
    p_rb.add_argument("--dry-run", action="store_true")
    p_rb.set_defaults(func=_cmd_ranking_batch)

    # bias-report (T113, B-04): 매월 1일 09:00 cron (`0 9 1 * *`)
    p_br = subparsers.add_parser(
        "bias-report",
        help="월간 편향 밸런스 리포트 생성 (FR-038, SC-011, SC-012)",
    )
    p_br.add_argument("--month", default=None, help="YYYY-MM 또는 YYYY-MM-DD. 기본=지난달")
    p_br.add_argument("--dry-run", action="store_true", help="계산만 하고 DB 저장 스킵")
    p_br.set_defaults(func=_cmd_bias_report)

    # Remaining stubs (Phase 8+)
    for name in (
        "pipeline",
        "youtube-auth",
        "whitelist-seed",
    ):
        p = subparsers.add_parser(name, help="(미구현 — 후속 태스크)")
        p.set_defaults(func=_cmd_stub(name))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
