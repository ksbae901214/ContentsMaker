"""039 Phase 4 — 업로드 CLI 테스트. 실제 업로드는 전부 주입한다."""
import json

import pytest

from scripts.auto_daily.upload_shorts import (
    UploadMetadata, metadata_from_config, parse_upload_package, publish,
    record_publish, youtube_category_id,
)


def _cfg(category="political"):
    return {
        "category": category,
        "slug": "20260826_test_v2_2",
        "title": "상단 제목",
        "yt_title": "13시간 만에 뒤집힌 사퇴 #장동혁",
        "persons": ["장동혁"],
        "scenes": [
            {"mode": "clip", "source": "main", "text": "\"저는 사퇴하지\n않습니다\""},
            {"mode": "tts", "source": "main", "text": "결국\n대표직 사퇴",
             "voice": "장동혁 대표는 13시간 만에 사퇴했습니다."},
        ],
        "sources": {"main": {"query": "q"}},
    }


# ── 메타데이터 ──────────────────────────────────────────────────────
def test_config에서_제목과_해시태그를_만든다():
    md = metadata_from_config(_cfg())
    assert md.title == "13시간 만에 뒤집힌 사퇴"       # 제목의 해시태그는 떼어낸다
    assert "#장동혁" in md.description


def test_유튜브_태그에는_샵을_붙이지_않는다():
    """API 는 태그를 평문으로 받는다. '#' 이 붙으면 태그가 깨진다."""
    md = metadata_from_config(_cfg())
    assert md.tags
    assert all(not t.startswith("#") for t in md.tags)


def test_고정댓글이_채워진다():
    assert metadata_from_config(_cfg()).pinned_comment


@pytest.mark.parametrize("category,expected", [
    ("political", "25"), ("economic", "25"), ("society", "25"),
    ("entertainment", "24"),
])
def test_카테고리별_유튜브_카테고리ID(category, expected):
    assert youtube_category_id(category) == expected


def test_연예는_엔터테인먼트_카테고리로_올린다():
    assert metadata_from_config(_cfg("entertainment")).category_id == "24"


def test_제목이_100자를_넘지_않는다():
    cfg = _cfg()
    cfg["yt_title"] = "가" * 200
    assert len(metadata_from_config(cfg).title) <= 100


# ── 사람이 손댄 upload_package.md 우선 ──────────────────────────────
_MD = """# 업로드 패키지 — 20260826_test_v2_2

**영상**: `data/x/final.mp4`

## 제목 (A/B)
- A: 사람이 고친 제목
- B: 대안 제목

## 3줄요약
한 줄
두 줄

## 설명
```
설명 본문입니다
#장동혁 #정치
```

## 해시태그
#장동혁 #정치

## 고정댓글
```
누구 책임일까요? ① 당 ② 본인
```
"""


def test_md의_A안_제목을_쓴다():
    """검수자가 md 에서 제목을 고쳤다면 그게 최종이다."""
    assert parse_upload_package(_MD).title == "사람이 고친 제목"


def test_md의_설명과_고정댓글을_읽는다():
    md = parse_upload_package(_MD)
    assert md.description == "설명 본문입니다\n#장동혁 #정치"
    assert md.pinned_comment == "누구 책임일까요? ① 당 ② 본인"


def test_md의_해시태그가_태그로_들어간다():
    assert parse_upload_package(_MD).tags == ["장동혁", "정치"]


def test_제목섹션이_없으면_ValueError():
    with pytest.raises(ValueError, match="제목"):
        parse_upload_package("# 업로드 패키지\n\n내용 없음")


# ── 업로드 ──────────────────────────────────────────────────────────
def _md_obj():
    return UploadMetadata(title="제목", description="설명", tags=["정치"],
                          pinned_comment="댓글", category_id="25")


def test_유튜브와_틱톡_둘다_올린다(tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"x")
    seen = {}

    def yt(video_path, title, description, tags, category_id, privacy):
        seen["yt"] = (title, category_id, privacy)
        return "https://youtu.be/abc12345678"

    def tt(video_path, title):
        seen["tt"] = title
        return "publish-id-1"

    outcome = publish(video, _md_obj(), youtube_upload=yt, tiktok_upload=tt,
                      log_path=tmp_path / "publish_log.jsonl")
    assert outcome.youtube_url == "https://youtu.be/abc12345678"
    assert outcome.tiktok_publish_id == "publish-id-1"
    assert seen["yt"] == ("제목", "25", "public")


def test_틱톡은_초안이라_수동게시가_필요하다고_알린다(tmp_path):
    """API 가 SELF_ONLY 로 고정 — 심사 통과 전엔 공개 게시가 불가능하다."""
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")
    outcome = publish(video, _md_obj(),
                      youtube_upload=lambda **kw: "https://youtu.be/x",
                      tiktok_upload=lambda video_path, title: "pid",
                      log_path=tmp_path / "l.jsonl")
    assert outcome.tiktok_needs_manual_publish is True


def test_유튜브_실패해도_틱톡은_시도한다(tmp_path):
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")

    def yt(**kw):
        raise RuntimeError("quota exceeded")

    outcome = publish(video, _md_obj(), youtube_upload=yt,
                      tiktok_upload=lambda video_path, title: "pid",
                      log_path=tmp_path / "l.jsonl")
    assert outcome.youtube_url is None
    assert outcome.tiktok_publish_id == "pid"
    assert any("quota" in e for e in outcome.errors)


def test_영상이_없으면_아무것도_올리지_않는다(tmp_path):
    with pytest.raises(FileNotFoundError):
        publish(tmp_path / "없음.mp4", _md_obj(),
                youtube_upload=lambda **kw: "x",
                tiktok_upload=lambda video_path, title: "y",
                log_path=tmp_path / "l.jsonl")


def test_대상_플랫폼을_고를_수_있다(tmp_path):
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")
    called = {"tt": False}

    def tt(video_path, title):
        called["tt"] = True
        return "pid"

    outcome = publish(video, _md_obj(), targets=("youtube",),
                      youtube_upload=lambda **kw: "https://youtu.be/x",
                      tiktok_upload=tt, log_path=tmp_path / "l.jsonl")
    assert called["tt"] is False
    assert outcome.tiktok_publish_id is None


def test_고정댓글은_자동_게시되지만_고정은_수동이다(tmp_path):
    """YouTube Data API v3 에는 댓글 '고정' 엔드포인트가 없다."""
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")
    posted = {}

    def poster(video_id, text):
        posted["args"] = (video_id, text)
        return "comment-id"

    outcome = publish(video, _md_obj(),
                      youtube_upload=lambda **kw: "https://youtu.be/abc12345678",
                      tiktok_upload=lambda video_path, title: "pid",
                      comment_poster=poster, log_path=tmp_path / "l.jsonl")
    assert posted["args"] == ("abc12345678", "댓글")
    assert outcome.comment_needs_manual_pin is True


def test_댓글_게시_실패는_업로드를_되돌리지_않는다(tmp_path):
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")

    def poster(video_id, text):
        raise RuntimeError("comments disabled")

    outcome = publish(video, _md_obj(),
                      youtube_upload=lambda **kw: "https://youtu.be/abc12345678",
                      tiktok_upload=lambda video_path, title: "pid",
                      comment_poster=poster, log_path=tmp_path / "l.jsonl")
    assert outcome.youtube_url is not None
    assert any("comments disabled" in e for e in outcome.errors)


# ── 기록 ────────────────────────────────────────────────────────────
def test_업로드_이력을_jsonl로_남긴다(tmp_path):
    log = tmp_path / "publish_log.jsonl"
    record_publish(log, {"slug": "a", "platform": "youtube"})
    record_publish(log, {"slug": "b", "platform": "tiktok"})
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [r["slug"] for r in rows] == ["a", "b"]
    assert "recorded_at" in rows[0]


def test_기록_디렉터리가_없으면_만든다(tmp_path):
    log = tmp_path / "nested" / "publish_log.jsonl"
    record_publish(log, {"slug": "a"})
    assert log.exists()


def test_publish는_이력을_남긴다(tmp_path):
    video = tmp_path / "f.mp4"
    video.write_bytes(b"x")
    log = tmp_path / "l.jsonl"
    publish(video, _md_obj(), youtube_upload=lambda **kw: "https://youtu.be/x",
            tiktok_upload=lambda video_path, title: "pid", log_path=log)
    assert log.exists()
    assert "youtube" in log.read_text(encoding="utf-8")
