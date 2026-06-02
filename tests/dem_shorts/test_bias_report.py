"""T104: 월간 편향 리포트 테스트 (FR-038, SC-011, SC-012).

검증 시나리오:
1. UploadedShorts 집계 → person_shares/party_shares/template_usage 계산
2. 30% 초과 인물 → top_n_person_warning (SC-011)
3. 3인 합계(이재명·조국·정청래) > 60% → 권고 메시지 (SC-011)
4. 여성/청년 카테고리 점유율 < 40% → 차별화 미달 권고 (SC-012)
5. 월별 UNIQUE 보장 (같은 month 재생성 시 upsert)
6. 평균 risk_score 집계
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from src.dem_shorts.db import get_connection, init_db


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "state.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _ensure_politician(conn, name, category="fixed"):
    """이름으로 조회, 없으면 삽입."""
    row = conn.execute(
        "SELECT id FROM politicians WHERE name=?", (name,)
    ).fetchone()
    if row:
        return row[0]
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO politicians
          (name, party, role, bio, tone_guide, tier, category, is_active,
           added_at, updated_at)
        VALUES (?, '더불어민주당', '', '', '', 'pinned', ?, 1, ?, ?)
        """,
        (name, category, now, now),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM politicians WHERE name=?", (name,)
    ).fetchone()[0]


def _add_source_video(conn, video_id="v1"):
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO source_videos
          (video_id, title, published_at, duration_sec, session_type,
           status, created_at, updated_at)
        VALUES (?, 'title', ?, 300, 'committee', 'downloaded', ?, ?)
        """,
        (video_id, now, now, now),
    )
    conn.commit()


def _add_segment(conn, video_id, politician_id):
    conn.execute(
        """
        INSERT INTO speech_segments
          (source_video_id, politician_id, start_sec, end_sec, confidence,
           stt_text, recommendation_score)
        VALUES (?, ?, 0, 10, 0.9, '', 50)
        """,
        (video_id, politician_id),
    )
    conn.commit()
    return conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]


def _add_draft(conn, segment_id, subtitle_preset="default", risk_score=10.0):
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO shorts_drafts
          (segment_id, cut_start_sec, cut_end_sec, commentary_json,
           commentary_char_count, subtitle_preset, risk_score, status,
           created_at, updated_at)
        VALUES (?, 0, 30, '[]', 0, ?, ?, 'uploaded', ?, ?)
        """,
        (segment_id, subtitle_preset, risk_score, now, now),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _add_upload(conn, draft_id, video_id_suffix, published_at: date):
    """uploaded_shorts에 1개 등록. published_at은 해당 월을 결정."""
    now = published_at.isoformat() + "T12:00:00+09:00"
    conn.execute(
        """
        INSERT INTO uploaded_shorts
          (draft_id, final_mp4_path, youtube_video_id, title, description,
           tags, fact_links, uploaded_at, metrics_updated_at, published_at)
        VALUES (?, '/tmp/a.mp4', ?, 'T', 'NATV 국회방송',
                '[]', '[]', ?, ?, ?)
        """,
        (draft_id, f"yt_{video_id_suffix}", now, now, now),
    )
    conn.commit()


def _seed_upload(
    conn,
    politician_name: str,
    category: str,
    subtitle_preset: str,
    risk_score: float,
    published_month: date,
    vid_suffix: str,
):
    """한 줄 헬퍼: 정치인 → segment → draft → upload."""
    pid = _ensure_politician(conn, politician_name, category=category)
    video_id = f"v_{vid_suffix}"
    # source_videos UNIQUE check
    existing = conn.execute(
        "SELECT 1 FROM source_videos WHERE video_id=?", (video_id,)
    ).fetchone()
    if not existing:
        _add_source_video(conn, video_id=video_id)
    seg_id = _add_segment(conn, video_id, pid)
    draft_id = _add_draft(conn, seg_id, subtitle_preset=subtitle_preset, risk_score=risk_score)
    _add_upload(conn, draft_id, vid_suffix, published_at=published_month)


# ---------------------------------------------------------------------------
# generate_bias_report
# ---------------------------------------------------------------------------


def test_bias_report_person_shares_sum_to_one(db):
    """person_shares의 합은 1.0 (total_uploads > 0)."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 5), "a")
    _seed_upload(db, "조국", "fixed", "default", 20.0, date(2026, 3, 10), "b")
    _seed_upload(db, "이재명", "fixed", "default", 15.0, date(2026, 3, 15), "c")

    report = generate_bias_report(db, month=month)

    assert report.total_uploads == 3
    # 이재명 2/3 = 0.667
    assert report.person_shares["이재명"] == pytest.approx(2 / 3, rel=1e-3)
    assert report.person_shares["조국"] == pytest.approx(1 / 3, rel=1e-3)
    assert sum(report.person_shares.values()) == pytest.approx(1.0)


def test_bias_report_warns_when_person_share_over_30_percent(db):
    """SC-011: 인물 점유율 30% 초과 → top_n_person_warning + 권고 메시지."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    # 이재명 4/5 = 80%
    for i in range(4):
        _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 1 + i), f"a{i}")
    _seed_upload(db, "조국", "fixed", "default", 10.0, date(2026, 3, 20), "b")

    report = generate_bias_report(db, month=month)

    assert "이재명" in report.top_n_person_warning
    # 권고 메시지에 이재명 + 퍼센트 포함
    joined = " ".join(report.recommendations)
    assert "이재명" in joined
    assert "30" in joined or "권장" in joined


def test_bias_report_warns_when_top3_sum_over_60_percent(db):
    """SC-011: 활성 perspective TOP 인물 합계 60% 초과 → 권고.

    2026-04-20: perspective='dem' 명시로 기존 dem TOP3 로직 검증.
    """
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    # Top3: 7/10 = 70%
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 1), "a")
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 2), "b")
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 3), "c")
    _seed_upload(db, "조국", "fixed", "default", 10.0, date(2026, 3, 4), "d")
    _seed_upload(db, "조국", "fixed", "default", 10.0, date(2026, 3, 5), "e")
    _seed_upload(db, "정청래", "fixed", "jungcheongrae", 10.0, date(2026, 3, 6), "f")
    _seed_upload(db, "정청래", "fixed", "jungcheongrae", 10.0, date(2026, 3, 7), "g")
    # 비Top3
    _seed_upload(db, "김영희", "female", "youth", 10.0, date(2026, 3, 8), "h")
    _seed_upload(db, "박민수", "youth", "youth", 10.0, date(2026, 3, 9), "i")
    _seed_upload(db, "이지훈", "female", "default", 10.0, date(2026, 3, 10), "j")

    report = generate_bias_report(db, month=month, perspective="dem")

    joined = " ".join(report.recommendations)
    # TOP 인물 합계 경고 (메시지 문구가 perspective 라벨 포함으로 변경됨)
    assert "TOP" in joined or "60" in joined or "합계" in joined


def test_bias_report_warns_when_female_youth_below_40_percent(db):
    """SC-012: 여성+청년 합계 < 40% → 차별화 미달 권고."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    # 여성/청년 = 1/5 = 20%
    for i in range(4):
        _seed_upload(db, f"남성의원{i}", "fixed", "default", 10.0, date(2026, 3, 1 + i), f"m{i}")
    _seed_upload(db, "여성의원", "female", "youth", 10.0, date(2026, 3, 20), "f1")

    report = generate_bias_report(db, month=month)

    joined = " ".join(report.recommendations)
    assert "40" in joined or "여성" in joined or "청년" in joined or "차별화" in joined


def test_bias_report_party_shares(db):
    """party_shares에 정당별 점유율 포함 (seed 정치인의 실제 소속 반영)."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    # 이재명·정청래 = 더불어민주당, 조국 = 조국혁신당 (seed)
    _seed_upload(db, "이재명", "fixed", "default", 10.0, date(2026, 3, 1), "a")
    _seed_upload(db, "정청래", "fixed", "default", 10.0, date(2026, 3, 2), "b")
    _seed_upload(db, "조국", "fixed", "default", 10.0, date(2026, 3, 3), "c")

    report = generate_bias_report(db, month=month)

    # 2/3 = 민주당, 1/3 = 조국혁신당
    assert report.party_shares["더불어민주당"] == pytest.approx(2 / 3, rel=1e-3)
    assert report.party_shares["조국혁신당"] == pytest.approx(1 / 3, rel=1e-3)


def test_bias_report_template_usage(db):
    """자막 프리셋(template_usage)별 사용 횟수 집계."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 1), "a")
    _seed_upload(db, "이재명", "fixed", "leejaemyung", 10.0, date(2026, 3, 2), "b")
    _seed_upload(db, "조국", "fixed", "default", 10.0, date(2026, 3, 3), "c")

    report = generate_bias_report(db, month=month)

    assert report.template_usage["leejaemyung"] == 2
    assert report.template_usage["default"] == 1


def test_bias_report_avg_risk_score(db):
    """avg_risk_score = sum(risk_score) / total_uploads."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    _seed_upload(db, "A", "fixed", "default", 10.0, date(2026, 3, 1), "a")
    _seed_upload(db, "B", "fixed", "default", 20.0, date(2026, 3, 2), "b")
    _seed_upload(db, "C", "fixed", "default", 30.0, date(2026, 3, 3), "c")

    report = generate_bias_report(db, month=month)

    assert report.avg_risk_score == pytest.approx(20.0)


def test_bias_report_empty_month_returns_zero_uploads(db):
    """업로드 0건인 월은 total_uploads=0, 빈 집계."""
    from src.dem_shorts.bias_report import generate_bias_report

    report = generate_bias_report(db, month=date(2025, 1, 1))

    assert report.total_uploads == 0
    assert report.person_shares == {}
    assert report.recommendations == ()


def test_bias_report_persist_upserts_row(db):
    """persist=True 시 bias_reports 테이블에 저장 + 동일 월 재실행 시 UPDATE."""
    from src.dem_shorts.bias_report import generate_bias_report

    month = date(2026, 3, 1)
    _seed_upload(db, "A", "fixed", "default", 10.0, date(2026, 3, 1), "a")

    generate_bias_report(db, month=month, persist=True)
    generate_bias_report(db, month=month, persist=True)  # 재실행

    rows = db.execute(
        "SELECT * FROM bias_reports WHERE month=?",
        (month.isoformat(),),
    ).fetchall()
    assert len(rows) == 1


def test_bias_report_only_counts_uploads_in_target_month(db):
    """다른 월 업로드는 집계에서 제외."""
    from src.dem_shorts.bias_report import generate_bias_report

    # 3월 2건, 4월 1건
    _seed_upload(db, "A", "fixed", "default", 10.0, date(2026, 3, 5), "a")
    _seed_upload(db, "A", "fixed", "default", 10.0, date(2026, 3, 15), "b")
    _seed_upload(db, "B", "fixed", "default", 10.0, date(2026, 4, 1), "c")

    report = generate_bias_report(db, month=date(2026, 3, 1))
    assert report.total_uploads == 2
    assert "B" not in report.person_shares


def test_resolve_previous_month():
    """helper: 주어진 날짜의 '지난 달 1일'."""
    from src.dem_shorts.bias_report import resolve_previous_month

    assert resolve_previous_month(date(2026, 4, 16)) == date(2026, 3, 1)
    assert resolve_previous_month(date(2026, 1, 5)) == date(2025, 12, 1)
    assert resolve_previous_month(date(2026, 3, 1)) == date(2026, 2, 1)
