"""T122/T123: 엔드투엔드 스모크 파이프라인 (R-15, 원칙 VII).

샘플 영상 1개를 입력받아 전체 파이프라인을 한 번 통과시킨다.
운영자가 새 환경에서 정합성을 빠르게 점검하거나 CI 가드레일로 사용.

기본은 stub 모드: Whisper/pyannote/Claude CLI/Remotion 모두 우회. 파이프라인
wiring 과 DB 트랜잭션 / 게이트 통과 경로를 검증한다.
`real_models=True` 면 실제 모델까지 호출 (시간 5~10분).
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.dem_shorts.compliance.gate import GateContext, validate
from src.dem_shorts.db import get_connection
from src.dem_shorts.drafts_repo import create_draft, update_draft
from src.dem_shorts.renderer import render_draft
from src.dem_shorts.scoring import DemScoreInputs, calculate_dem_score
from src.dem_shorts.speaker_id.identify import identify_speakers
from src.dem_shorts.utils import paths as paths_mod

logger = logging.getLogger(__name__)


SMOKE_VIDEO_ID = "smoke_natv_001"
# DEFAULT_PERSPECTIVE(ppp) 기본 인물. dem 스모크는 명시 인자로만.
SMOKE_POLITICIAN = "한동훈"  # init_db seed 에 이미 존재 (pinned/fixed, perspective=ppp)


# ---------------------------------------------------------------------------
# stub 데이터 작성기
# ---------------------------------------------------------------------------


def _write_stub_transcript(video_id: str) -> Path:
    """한동훈 대표 발언이 포함된 가짜 transcript JSON.

    identify_speakers 가 호명 패턴 매칭으로 정치인을 식별할 수 있도록
    "한동훈 대표" 키워드를 포함시킨다.
    """
    # SPEAKER_CONFIDENCE_MIN=0.7 → 같은 화자에 대해 3회 이상 호명 필요
    # confidence = mentions / (mentions + 1) ≥ 0.7 → mentions ≥ 3
    payload = {
        "video_id": video_id,
        "language": "ko",
        "model": "stub-large-v3",
        "segments": [
            {
                "start": 0.0,
                "end": 6.0,
                "text": "다음 발언자는 한동훈 대표입니다.",
            },
            {
                "start": 6.0,
                "end": 20.0,
                "text": "한동훈 대표이 민생 정책에 대해 발언합니다.",
            },
            {
                "start": 20.0,
                "end": 40.0,
                "text": "한동훈 대표, 경제 위기 극복 방안을 제시해주십시오.",
            },
            {
                "start": 40.0,
                "end": 60.0,
                "text": "국민의 삶을 바꾸는 정치를 하겠습니다.",
            },
        ],
    }
    out = paths_mod.transcript_path(video_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _write_stub_diarization(video_id: str) -> Path:
    """단일 화자(SPEAKER_00) 4 턴 가짜 diarization.

    identify_speakers 의 confidence 공식 = 호명수/(호명수+1) 이 0.7 이상이려면
    같은 클러스터에서 호명 이벤트가 ≥3 회 누적되어야 함 → 4 턴(각각에 호명 포함).
    """
    payload = {
        "video_id": video_id,
        "model": "stub-pyannote-3.1",
        "speakers": [
            {"start": 0.0, "end": 6.0, "speaker_cluster": "SPEAKER_00"},
            {"start": 6.0, "end": 20.0, "speaker_cluster": "SPEAKER_00"},
            {"start": 20.0, "end": 40.0, "speaker_cluster": "SPEAKER_00"},
            {"start": 40.0, "end": 60.0, "speaker_cluster": "SPEAKER_00"},
        ],
    }
    out = paths_mod.segments_path(video_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _stub_commentary_blocks() -> list[dict]:
    """COMMENTARY_MIN_CHARS(50자) 이상, 30%+ 시간 커버하는 stub."""
    return [
        {
            "start": 1.0,
            "end": 14.0,
            "text": (
                "한동훈 대표이 민생 회복 정책을 제안하며 "
                "경제 위기 극복 방안과 국민 삶의 질 향상을 강조했습니다."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# 단계별 헬퍼
# ---------------------------------------------------------------------------


def _ensure_source_video(conn, *, video_id: str, sample_path: Path) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO source_videos
          (video_id, title, description, published_at, duration_sec,
           thumbnail_url, session_type, download_path, dem_score,
           status, created_at, updated_at)
        VALUES (?, ?, '', ?, 600, '', 'plenary', ?, 80.0, 'ready', ?, ?)
        """,
        (
            video_id,
            f"[SMOKE] {video_id}",
            now,
            str(sample_path),
            now,
            now,
        ),
    )
    conn.commit()
    return {"video_id": video_id, "duration_sec": 600}


def _run_stt(video_id: str, *, sample_path: Path, real_models: bool) -> dict:
    if real_models:
        from src.dem_shorts.stt import transcribe_video

        out = transcribe_video(sample_path, video_id=video_id)
    else:
        out = _write_stub_transcript(video_id)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"path": str(out), "segments": len(data.get("segments", []))}


def _run_diarization(video_id: str, *, sample_path: Path, real_models: bool) -> dict:
    if real_models:
        from src.dem_shorts.diarization import diarize_video

        out = diarize_video(sample_path, video_id=video_id)
    else:
        out = _write_stub_diarization(video_id)
    data = json.loads(out.read_text(encoding="utf-8"))
    return {"path": str(out), "turns": len(data.get("speakers", []))}


def _run_identify(conn, video_id: str) -> dict:
    saved = identify_speakers(conn, video_id)
    return {"saved_segments": saved}


def _run_score(conn, video_id: str) -> dict:
    inputs = DemScoreInputs(
        dem_person_count=1,
        has_top_whitelist=True,
        top3_present={SMOKE_POLITICIAN: True},
        female_or_youth_present=False,
        issue_keyword_matches=1,
        duration_sec=600,
        recent_repeat_count=0,
    )
    score = calculate_dem_score(inputs)
    conn.execute(
        "UPDATE source_videos SET dem_score=? WHERE video_id=?",
        (score, video_id),
    )
    conn.commit()
    return {"dem_score": score}


def _create_smoke_draft(conn, video_id: str) -> dict:
    """첫 segment를 cut 해 draft 생성. commentary + fact_links 포함."""
    seg_row = conn.execute(
        "SELECT id, start_sec, end_sec FROM speech_segments "
        "WHERE source_video_id=? ORDER BY id LIMIT 1",
        (video_id,),
    ).fetchone()
    if not seg_row:
        raise RuntimeError("smoke: identify 후 speech_segments 가 없음")

    blocks = _stub_commentary_blocks()

    draft = create_draft(
        conn,
        {
            "segment_id": seg_row["id"],
            "cut_start_sec": float(seg_row["start_sec"]),
            "cut_end_sec": min(
                float(seg_row["end_sec"]),
                float(seg_row["start_sec"]) + 30.0,
            ),
            "subtitle_preset": "default",
        },
    )
    # commentary_blocks · fact_source_urls 는 별도 PATCH (create_draft 미수용 필드)
    draft = update_draft(
        conn,
        draft["id"],
        {
            "commentary_blocks": blocks,
            "fact_source_urls": [
                "https://natv.example.com/v/" + video_id,
                "https://news.example.com/article/abcd",
            ],
        },
    )
    return draft


def _run_gate(draft_id: int, *, operator_id: str, db_path: Path) -> dict:
    ctx = GateContext(
        draft_id=draft_id,
        manual_fact_check_signed_by=operator_id,
        manual_defamation_check_signed_by=operator_id,
        operator_id=operator_id,
        db_path=db_path,
    )
    result = validate(ctx)
    return {
        "passed": result.is_passed(),
        "overall_status": result.overall_status,
        "risk_score": result.risk_score,
    }


def _run_render(draft_id: int, *, db_path: Path, real_models: bool) -> dict:
    res = render_draft(draft_id, db_path=db_path, skip_remotion=not real_models)
    return {
        "rendered_path": str(res.rendered_path),
        "duration_sec": res.duration_sec,
        "used_cache": res.used_cache,
    }


# ---------------------------------------------------------------------------
# 메인 진입점
# ---------------------------------------------------------------------------


def run_e2e_smoke(
    *,
    sample_path: Path,
    db_path: Path,
    real_models: bool = False,
    operator_id: str = "smoke",
    video_id: str = SMOKE_VIDEO_ID,
) -> dict:
    """전체 파이프라인 1회 실행.

    Args:
        sample_path: 샘플 NATV mp4 (real_models=True 일 때만 실제 사용).
        db_path: 격리된 SQLite 경로 (이미 init_db 완료 상태).
        real_models: True면 Whisper/pyannote/Remotion 실제 호출.
        operator_id: 게이트 manual sign 명의.
        video_id: 사용할 source_videos.video_id.

    Returns:
        {"phases": {...단계별 결과...}, "ok": True}
    """
    if real_models and not sample_path.exists():
        raise FileNotFoundError(f"smoke sample not found: {sample_path}")

    phases: dict[str, dict] = {}

    @contextmanager
    def _timed(name: str):
        t0 = time.perf_counter()
        bucket: dict = {}
        try:
            yield bucket
        finally:
            bucket["elapsed_sec"] = round(time.perf_counter() - t0, 3)
            phases[name] = {**phases.get(name, {}), **bucket}

    with _timed("source_video") as bkt:
        with get_connection(db_path) as conn:
            bkt.update(_ensure_source_video(conn, video_id=video_id, sample_path=sample_path))

    with _timed("stt") as bkt:
        bkt.update(_run_stt(video_id, sample_path=sample_path, real_models=real_models))

    with _timed("diarize") as bkt:
        bkt.update(_run_diarization(video_id, sample_path=sample_path, real_models=real_models))

    with _timed("identify") as bkt:
        with get_connection(db_path) as conn:
            bkt.update(_run_identify(conn, video_id))

    with _timed("score") as bkt:
        with get_connection(db_path) as conn:
            bkt.update(_run_score(conn, video_id))

    with _timed("draft") as bkt:
        with get_connection(db_path) as conn:
            draft = _create_smoke_draft(conn, video_id)
            bkt["draft_id"] = draft["id"]

    with _timed("gate") as bkt:
        bkt.update(_run_gate(draft["id"], operator_id=operator_id, db_path=db_path))
    if not phases["gate"].get("passed"):
        raise RuntimeError(f"smoke: 게이트 미통과 — {phases['gate']}")

    with _timed("render") as bkt:
        bkt.update(_run_render(draft["id"], db_path=db_path, real_models=real_models))

    total_elapsed = round(sum(p.get("elapsed_sec", 0.0) for p in phases.values()), 3)
    summary = {
        "ok": True,
        "video_id": video_id,
        "real_models": real_models,
        "total_elapsed_sec": total_elapsed,
        "phases": phases,
    }
    logger.info("e2e smoke done: %s", summary)
    return summary
