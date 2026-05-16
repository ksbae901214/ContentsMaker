"""T118: YouTube 메트릭 갱신 배치 테스트 (B-05, FR-038 리포트 입력).

`update_metrics()` 가 uploaded_shorts의 view_count/like_count/comment_count/
metrics_updated_at을 YouTube videos.list 결과로 갱신하는지 검증.

- network 호출은 fetch_videos_stats() 를 monkeypatch 로 stub.
- 테이크다운 감지 (items 에서 사라진 video → is_taken_down=1, takedown_reason)
- 업로드 후 24시간 이내는 "fresh" 로 더 자주 갱신되는 동작은 is_fresh() 헬퍼로 확인.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.dem_shorts.db import get_connection, init_db


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "state.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        yield conn


def _add_politician(conn, name="이재명", category="fixed"):
    """이재명/조국/정청래는 init_db seed로 이미 들어 있으므로 upsert 패턴."""
    row = conn.execute("SELECT id FROM politicians WHERE name=?", (name,)).fetchone()
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
    return conn.execute("SELECT id FROM politicians WHERE name=?", (name,)).fetchone()[0]


def _add_source_video(conn, vid="v1"):
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO source_videos
          (video_id, title, published_at, duration_sec, session_type,
           status, created_at, updated_at)
        VALUES (?, 't', ?, 300, 'committee', 'downloaded', ?, ?)
        """,
        (vid, now, now, now),
    )
    conn.commit()
    return vid


def _add_segment(conn, vid, pid):
    conn.execute(
        """
        INSERT INTO speech_segments
          (source_video_id, politician_id, start_sec, end_sec, confidence,
           stt_text, recommendation_score)
        VALUES (?, ?, 0, 10, 0.9, '', 50)
        """,
        (vid, pid),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _add_draft(conn, seg_id):
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO shorts_drafts
          (segment_id, cut_start_sec, cut_end_sec, commentary_json,
           commentary_char_count, subtitle_preset, risk_score, status,
           created_at, updated_at)
        VALUES (?, 0, 30, '[]', 0, 'default', 5.0, 'uploaded', ?, ?)
        """,
        (seg_id, now, now),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _add_upload(
    conn,
    draft_id,
    yt_id,
    *,
    uploaded_at: datetime,
    view_count: int = 0,
    like_count: int = 0,
    comment_count: int = 0,
    is_taken_down: int = 0,
):
    ts = uploaded_at.isoformat()
    conn.execute(
        """
        INSERT INTO uploaded_shorts
          (draft_id, final_mp4_path, youtube_video_id, title, description,
           tags, fact_links, uploaded_at, metrics_updated_at, published_at,
           view_count, like_count, comment_count, is_taken_down)
        VALUES (?, '/tmp/a.mp4', ?, 'T', 'NATV 국회방송',
                '[]', '[]', ?, ?, ?, ?, ?, ?, ?)
        """,
        (draft_id, yt_id, ts, ts, ts, view_count, like_count, comment_count, is_taken_down),
    )
    conn.commit()


def _seed_upload(conn, yt_id, uploaded_at, vid="v1", name="이재명"):
    pid = _add_politician(conn, name=name)
    _add_source_video(conn, vid=vid)
    seg = _add_segment(conn, vid, pid)
    draft = _add_draft(conn, seg)
    _add_upload(conn, draft, yt_id, uploaded_at=uploaded_at)
    return draft


# ---------------------------------------------------------------------------
# fresh window 판정
# ---------------------------------------------------------------------------


def test_is_fresh_true_within_24_hours():
    from src.dem_shorts.metrics_updater import is_fresh

    now = datetime.now(timezone.utc)
    assert is_fresh(now - timedelta(hours=1), now=now) is True
    assert is_fresh(now - timedelta(hours=23, minutes=30), now=now) is True


def test_is_fresh_false_after_24_hours():
    from src.dem_shorts.metrics_updater import is_fresh

    now = datetime.now(timezone.utc)
    assert is_fresh(now - timedelta(hours=25), now=now) is False
    assert is_fresh(now - timedelta(days=7), now=now) is False


# ---------------------------------------------------------------------------
# select_targets
# ---------------------------------------------------------------------------


def test_select_targets_excludes_taken_down(db):
    """is_taken_down=1 인 업로드는 fetch 대상에서 제외."""
    from src.dem_shorts.metrics_updater import select_targets

    now_dt = datetime.now(timezone.utc)
    pid = _add_politician(db)
    _add_source_video(db, vid="v1")
    seg = _add_segment(db, "v1", pid)
    draft = _add_draft(db, seg)
    _add_upload(db, draft, "yt_ok", uploaded_at=now_dt)

    _add_source_video(db, vid="v2")
    seg2 = _add_segment(db, "v2", pid)
    draft2 = _add_draft(db, seg2)
    _add_upload(db, draft2, "yt_down", uploaded_at=now_dt, is_taken_down=1)

    targets = select_targets(db, limit=50)
    ids = [t["youtube_video_id"] for t in targets]
    assert "yt_ok" in ids
    assert "yt_down" not in ids


def test_select_targets_respects_limit(db):
    from src.dem_shorts.metrics_updater import select_targets

    now_dt = datetime.now(timezone.utc)
    for i in range(5):
        _seed_upload(db, f"yt_{i}", now_dt, vid=f"v{i}", name=f"정치인{i}")

    targets = select_targets(db, limit=3)
    assert len(targets) == 3


# ---------------------------------------------------------------------------
# update_metrics — 주 시나리오
# ---------------------------------------------------------------------------


def test_update_metrics_applies_stats_from_stub(db, monkeypatch):
    """fetch_videos_stats stub 결과가 uploaded_shorts에 반영되는지 검증."""
    from src.dem_shorts import metrics_updater

    now_dt = datetime.now(timezone.utc)
    _seed_upload(db, "yt_aaa", now_dt, vid="v1", name="이재명")
    _seed_upload(db, "yt_bbb", now_dt, vid="v2", name="조국")

    def _stub(video_ids, *, api_key=None):
        return {
            "yt_aaa": {"view_count": 12345, "like_count": 678, "comment_count": 9},
            "yt_bbb": {"view_count": 42, "like_count": 1, "comment_count": 0},
        }

    monkeypatch.setattr(metrics_updater, "fetch_videos_stats", _stub)

    summary = metrics_updater.update_metrics(db)
    assert summary["updated"] == 2
    assert summary["taken_down"] == 0

    row = db.execute(
        "SELECT view_count, like_count, comment_count, is_taken_down "
        "FROM uploaded_shorts WHERE youtube_video_id='yt_aaa'"
    ).fetchone()
    assert row["view_count"] == 12345
    assert row["like_count"] == 678
    assert row["comment_count"] == 9
    assert row["is_taken_down"] == 0


def test_update_metrics_detects_takedown(db, monkeypatch):
    """YouTube API 응답에 video_id가 없으면 is_taken_down=1, takedown_reason 기록."""
    from src.dem_shorts import metrics_updater

    now_dt = datetime.now(timezone.utc) - timedelta(days=2)
    _seed_upload(db, "yt_gone", now_dt, vid="v1", name="이재명")

    def _stub(video_ids, *, api_key=None):
        return {}  # 전혀 응답 없음 — 테이크다운으로 간주

    monkeypatch.setattr(metrics_updater, "fetch_videos_stats", _stub)

    summary = metrics_updater.update_metrics(db)
    assert summary["taken_down"] == 1

    row = db.execute(
        "SELECT is_taken_down, takedown_reason FROM uploaded_shorts "
        "WHERE youtube_video_id='yt_gone'"
    ).fetchone()
    assert row["is_taken_down"] == 1
    assert row["takedown_reason"]  # not empty


def test_update_metrics_touches_metrics_updated_at(db, monkeypatch):
    """metrics_updated_at이 최신 시각으로 갱신된다."""
    from src.dem_shorts import metrics_updater

    old_ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
    _seed_upload(db, "yt_aaa", old_ts)

    def _stub(video_ids, *, api_key=None):
        return {"yt_aaa": {"view_count": 1, "like_count": 0, "comment_count": 0}}

    monkeypatch.setattr(metrics_updater, "fetch_videos_stats", _stub)

    metrics_updater.update_metrics(db)
    row = db.execute(
        "SELECT metrics_updated_at FROM uploaded_shorts WHERE youtube_video_id='yt_aaa'"
    ).fetchone()
    new_ts = datetime.fromisoformat(row["metrics_updated_at"])
    # old_ts(2025-01-01) 보다 훨씬 이후여야 함
    assert new_ts > old_ts + timedelta(days=1)


def test_update_metrics_dry_run_does_not_write(db, monkeypatch):
    from src.dem_shorts import metrics_updater

    now_dt = datetime.now(timezone.utc)
    _seed_upload(db, "yt_aaa", now_dt)

    def _stub(video_ids, *, api_key=None):
        return {"yt_aaa": {"view_count": 99, "like_count": 5, "comment_count": 2}}

    monkeypatch.setattr(metrics_updater, "fetch_videos_stats", _stub)

    summary = metrics_updater.update_metrics(db, dry_run=True)
    assert summary["updated"] == 1
    assert summary["dry_run"] is True

    row = db.execute(
        "SELECT view_count FROM uploaded_shorts WHERE youtube_video_id='yt_aaa'"
    ).fetchone()
    assert row["view_count"] == 0  # 변화 없음


def test_update_metrics_empty_targets_noop(db, monkeypatch):
    """업로드 기록이 전혀 없을 때 정상 종료."""
    from src.dem_shorts import metrics_updater

    def _stub(video_ids, *, api_key=None):
        # 빈 입력이 들어오면 호출되지 않아야 함
        raise AssertionError("fetch should not be called when no targets")

    monkeypatch.setattr(metrics_updater, "fetch_videos_stats", _stub)
    summary = metrics_updater.update_metrics(db)
    assert summary["updated"] == 0
    assert summary["taken_down"] == 0
