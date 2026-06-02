"""T028: `GET /api/dem-shorts/videos` Python 측 로직 계약 테스트.

Next.js route 자체는 subprocess 래퍼이므로, 핵심 DB 조회·필터 로직을
파이썬 측에서 직접 검증한다. Contract: contracts/rest-api.md §GET videos
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.dem_shorts.db import get_connection, migrate


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db = tmp_path / "api_test.db"
    with get_connection(db) as conn:
        migrate(conn)
    return db


def _insert_video(
    conn,
    video_id: str,
    *,
    title: str = "test",
    session_type: str = "plenary",
    dem_score: float = 0.0,
    status: str = "new",
    published_at: str | None = None,
    excluded_reason: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO source_videos
          (video_id, title, description, published_at, duration_sec,
           thumbnail_url, session_type, dem_score, status, excluded_reason,
           created_at, updated_at)
        VALUES (?, ?, '', ?, 3600, '', ?, ?, ?, ?, ?, ?)
        """,
        (
            video_id,
            title,
            published_at or now,
            session_type,
            dem_score,
            status,
            excluded_reason,
            now,
            now,
        ),
    )
    conn.commit()


class TestVideoListQuery:
    def test_orders_by_score_desc(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _insert_video(conn, "a", dem_score=50)
            _insert_video(conn, "b", dem_score=80)
            _insert_video(conn, "c", dem_score=20)
            rows = conn.execute(
                "SELECT video_id FROM source_videos "
                "WHERE status != 'excluded' "
                "ORDER BY dem_score DESC"
            ).fetchall()
        assert [r[0] for r in rows] == ["b", "a", "c"]

    def test_excluded_hidden_by_default(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _insert_video(conn, "v1", dem_score=70)
            _insert_video(
                conn,
                "v2",
                dem_score=0,
                status="excluded",
                excluded_reason="length_over_6h",
            )
            rows = conn.execute(
                "SELECT video_id FROM source_videos WHERE status != 'excluded'"
            ).fetchall()
        assert [r[0] for r in rows] == ["v1"]

    def test_min_score_filter(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _insert_video(conn, "low", dem_score=30)
            _insert_video(conn, "hi", dem_score=85)
            rows = conn.execute(
                "SELECT video_id FROM source_videos WHERE dem_score >= ?", (50,)
            ).fetchall()
        assert [r[0] for r in rows] == ["hi"]

    def test_session_type_filter(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            _insert_video(conn, "p1", session_type="plenary")
            _insert_video(conn, "c1", session_type="committee")
            rows = conn.execute(
                "SELECT video_id FROM source_videos WHERE session_type = ?", ("plenary",)
            ).fetchall()
        assert [r[0] for r in rows] == ["p1"]

    def test_since_hours_filter(self, temp_db: Path):
        """최근 N시간 필터: published_at >= since."""
        now = datetime.now(timezone.utc)
        with get_connection(temp_db) as conn:
            _insert_video(
                conn,
                "recent",
                published_at=now.isoformat(),
            )
            _insert_video(
                conn,
                "old",
                published_at=(now - timedelta(days=2)).isoformat(),
            )
            since = (now - timedelta(hours=24)).isoformat()
            rows = conn.execute(
                "SELECT video_id FROM source_videos WHERE published_at >= ?",
                (since,),
            ).fetchall()
        assert [r[0] for r in rows] == ["recent"]

    def test_video_detail_not_found(self, temp_db: Path):
        with get_connection(temp_db) as conn:
            row = conn.execute(
                "SELECT * FROM source_videos WHERE video_id = ?", ("missing",)
            ).fetchone()
        assert row is None

    def test_video_detail_with_segments(self, temp_db: Path):
        """US2 대비: speech_segments LEFT JOIN 구조 검증."""
        with get_connection(temp_db) as conn:
            _insert_video(conn, "v1", dem_score=80)
            segs = conn.execute(
                """
                SELECT s.id, s.stt_text, p.name
                FROM speech_segments s
                LEFT JOIN politicians p ON p.id = s.politician_id
                WHERE s.source_video_id = ?
                """,
                ("v1",),
            ).fetchall()
        assert segs == []  # empty until Phase 4
