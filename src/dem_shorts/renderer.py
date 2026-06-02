"""T083: Dem-Shorts 렌더러 — Remotion + FFmpeg 통합 (FR-033, FR-034, R-14).

파이프라인:
1. 게이트 통과 재확인 (이중 방어, SC-005)
2. segment cut (원본 9:16 변환) — 스마트 캐싱
3. TTS 합성 (필요 시)
4. Remotion DemShortsComposition 렌더 → MP4
5. 최종 산출물 경로를 shorts_drafts.rendered_path 저장
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.dem_shorts.compliance.gate import get_latest_result
from src.dem_shorts.db import get_connection
from src.dem_shorts.editor.bgm_manifest import validate_bgm_filename
from src.dem_shorts.editor.segment_cutter import cut_segment
from src.dem_shorts.editor.subtitle_presets import get_preset, preset_to_dict
from src.dem_shorts.editor.tts_integration import synthesize_blocks
from src.dem_shorts.utils.paths import (
    ARCHIVE_DIR,
    DB_PATH,
    OUTPUTS_DIR,
    output_path,
)

logger = logging.getLogger(__name__)

REMOTION_ROOT = Path("src/video/remotion")
REMOTION_PUBLIC = REMOTION_ROOT / "public"


class RenderError(Exception):
    """Raised when render fails."""


@dataclass(frozen=True)
class RenderResult:
    draft_id: int
    rendered_path: Path
    duration_sec: float
    cache_key: str
    used_cache: bool


def verify_gate_passed(draft_id: int, *, db_path: Path | None = None) -> None:
    """⭐ 이중 방어: render API 호출 전 게이트 통과 재확인 (SC-005).

    저장된 ComplianceGateResult를 로드해 `is_passed()`로 재검증.
    DB 수동 조작으로 overall_status만 'pass'로 바꿔도 실제 아이템/서명/점수를
    재체크하므로 거부됨.
    """
    result = get_latest_result(draft_id, db_path=db_path)
    if result is None:
        raise RenderError(
            f"gate_not_executed: draft {draft_id}에 대해 먼저 /gate를 실행해야 합니다."
        )
    if not result.is_passed():
        raise RenderError(
            f"gate_not_passed: draft {draft_id} (overall={result.overall_status}, "
            f"risk={result.risk_score}, 서명={bool(result.manual_fact_check_signed_by)}/"
            f"{bool(result.manual_defamation_check_signed_by)})"
        )


def compute_render_cache_key(draft_data: dict) -> str:
    """스마트 캐싱용 키 — 렌더 출력에 영향을 주는 필드만 해싱."""
    cache_input = {
        "id": draft_data.get("id"),
        "segment_id": draft_data.get("segment_id"),
        "cut_start_sec": draft_data.get("cut_start_sec"),
        "cut_end_sec": draft_data.get("cut_end_sec"),
        "commentary_blocks": draft_data.get("commentary_blocks"),
        "subtitle_preset": draft_data.get("subtitle_preset"),
        "tts_voice": draft_data.get("tts_voice"),
        "tts_enabled": draft_data.get("tts_enabled"),
        "bgm_filename": draft_data.get("bgm_filename"),
    }
    s = json.dumps(cache_input, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _load_draft(conn, draft_id: int) -> dict:
    row = conn.execute("SELECT * FROM shorts_drafts WHERE id=?", (draft_id,)).fetchone()
    if not row:
        raise RenderError(f"draft_not_found: id={draft_id}")
    d = dict(row)
    d["commentary_blocks"] = json.loads(d.get("commentary_json") or "[]")
    d["fact_source_urls"] = json.loads(d.get("fact_source_urls") or "[]")
    return d


def _load_source_video_id(conn, segment_id: int) -> str:
    row = conn.execute(
        "SELECT source_video_id FROM speech_segments WHERE id=?", (segment_id,)
    ).fetchone()
    if not row:
        raise RenderError(f"segment_not_found: id={segment_id}")
    return row[0]


def _copy_to_public(src: Path, dest_filename: str) -> str:
    """Remotion이 staticFile로 로드하도록 public/ 하위에 복사."""
    REMOTION_PUBLIC.mkdir(parents=True, exist_ok=True)
    dest = REMOTION_PUBLIC / dest_filename
    shutil.copy(src, dest)
    return dest_filename


def _run_remotion(
    *,
    composition_id: str,
    props_json: str,
    output: Path,
) -> None:
    """Remotion CLI로 MP4 렌더. 기존 video/renderer.py와 유사 패턴."""
    if shutil.which("npx") is None:
        raise RenderError("npx not available — Node.js required for Remotion")

    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        composition_id,
        str(output.resolve()),
        "--props",
        props_json,
        "--codec",
        "h264",
    ]
    result = subprocess.run(
        cmd,
        cwd=REMOTION_ROOT,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RenderError(
            f"remotion render failed (exit {result.returncode}): {result.stderr[:500]}"
        )
    if not output.exists():
        raise RenderError(f"remotion output missing: {output}")


def render_draft(
    draft_id: int,
    *,
    db_path: Path | None = None,
    skip_remotion: bool = False,  # 테스트 용 (실제 렌더 비용 절약)
) -> RenderResult:
    """컴플라이언스 게이트 통과한 draft를 MP4로 렌더.

    Raises:
        RenderError: 게이트 미통과 / 필수 파일 누락 / FFmpeg/Remotion 실패.
    """
    path = db_path or DB_PATH

    # 1) ⭐ 게이트 이중 방어
    verify_gate_passed(draft_id, db_path=path)

    with get_connection(path) as conn:
        draft = _load_draft(conn, draft_id)
        source_video_id = _load_source_video_id(conn, draft["segment_id"])

    # 2) BGM 등록 확인 (FR-035)
    validate_bgm_filename(draft.get("bgm_filename"))

    cache_key = compute_render_cache_key(draft)
    final_out = output_path(draft_id)
    cache_marker = final_out.with_suffix(".cache.txt")

    # Smart cache: 같은 입력 → 기존 출력 재사용
    if final_out.exists() and cache_marker.exists() and cache_marker.read_text().strip() == cache_key:
        logger.info("render: cache hit draft=%d key=%s", draft_id, cache_key)
        return RenderResult(
            draft_id=draft_id,
            rendered_path=final_out,
            duration_sec=draft["cut_end_sec"] - draft["cut_start_sec"],
            cache_key=cache_key,
            used_cache=True,
        )

    if skip_remotion:
        # Dry run — 빈 파일 생성 후 반환 (테스트용)
        final_out.parent.mkdir(parents=True, exist_ok=True)
        final_out.write_bytes(b"\x00")
        cache_marker.write_text(cache_key)
        return RenderResult(
            draft_id=draft_id,
            rendered_path=final_out,
            duration_sec=draft["cut_end_sec"] - draft["cut_start_sec"],
            cache_key=cache_key,
            used_cache=False,
        )

    # 3) 원본 영상 구간 자르기 + 9:16 변환
    src_archive = ARCHIVE_DIR / f"{source_video_id}.mp4"
    if not src_archive.exists():
        raise RenderError(f"archive not found: {src_archive}")
    cut_tmp = OUTPUTS_DIR / f"cut_{draft_id}_{cache_key}.mp4"
    cut_segment(
        input_path=src_archive,
        output_path=cut_tmp,
        start_sec=draft["cut_start_sec"],
        end_sec=draft["cut_end_sec"],
    )
    video_filename = _copy_to_public(cut_tmp, f"dem_cut_{draft_id}.mp4")

    # 4) TTS 합성
    tts_filename: str | None = None
    if draft.get("tts_enabled") and draft.get("tts_voice"):
        tts_dir = OUTPUTS_DIR / f"tts_{draft_id}"
        tts_files = synthesize_blocks(
            draft["commentary_blocks"], draft["tts_voice"], tts_dir
        )
        if tts_files:
            # 첫 블록만 사용 (단순화) — 복잡한 타이밍 믹싱은 FFmpeg로 별도 처리
            tts_filename = _copy_to_public(tts_files[0], f"dem_tts_{draft_id}.mp3")

    # 5) BGM 복사
    bgm_filename_public: str | None = None
    if draft.get("bgm_filename"):
        from src.dem_shorts.utils.paths import BGM_DIR
        bgm_src = BGM_DIR / draft["bgm_filename"]
        if bgm_src.exists():
            bgm_filename_public = _copy_to_public(bgm_src, f"dem_bgm_{draft_id}.mp3")

    # 6) Remotion props
    preset = get_preset(draft["subtitle_preset"])
    props = {
        "videoFile": video_filename,
        "commentaryBlocks": draft["commentary_blocks"],
        "subtitlePreset": preset_to_dict(preset),
        "ttsFile": tts_filename,
        "bgmFile": bgm_filename_public,
        "sourceLabelText": "NATV 국회방송",
    }
    props_json = json.dumps(props, ensure_ascii=False)

    # 7) Remotion 렌더
    _run_remotion(
        composition_id="DemShorts",
        props_json=props_json,
        output=final_out,
    )

    # 8) Cache marker + DB 업데이트
    cache_marker.write_text(cache_key)
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(path) as conn:
        conn.execute(
            "UPDATE shorts_drafts SET rendered_path=?, status='rendered', updated_at=? WHERE id=?",
            (str(final_out), now, draft_id),
        )
        conn.commit()

    return RenderResult(
        draft_id=draft_id,
        rendered_path=final_out,
        duration_sec=draft["cut_end_sec"] - draft["cut_start_sec"],
        cache_key=cache_key,
        used_cache=False,
    )
