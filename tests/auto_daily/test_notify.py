"""039 Phase 5 — 완료/보류 알림 테스트."""
from pathlib import Path

from scripts.auto_daily.notify import build_summary, notify
from scripts.auto_daily.review_gate import Decision


def test_보류_요약에_사유가_전부_들어간다():
    summary = build_summary(
        slot="morning",
        decision=Decision(False, ("정책상 전면 보류", "클립 비중 40% < 하한 65%")),
        video=Path("/x/final.mp4"), chat_block="제목: 사퇴")
    assert "보류" in summary
    assert "클립 비중" in summary
    assert "정책상 전면 보류" in summary


def test_게시_요약에는_업로드_결과가_들어간다():
    summary = build_summary(slot="noon", decision=Decision(True, ()),
                            video=Path("/x/final.mp4"), chat_block="제목: 금리",
                            youtube_url="https://youtu.be/abc")
    assert "https://youtu.be/abc" in summary


def test_틱톡은_수동게시_안내가_붙는다():
    """API 가 초안까지만 올린다 — 안내가 없으면 올라간 줄 안다."""
    summary = build_summary(slot="evening", decision=Decision(True, ()),
                            video=Path("/x/f.mp4"), chat_block="",
                            tiktok_publish_id="pid")
    assert "수동" in summary or "1탭" in summary


def test_고정댓글은_수동고정_안내가_붙는다():
    """YouTube API 에 댓글 고정 엔드포인트가 없다."""
    summary = build_summary(slot="morning", decision=Decision(True, ()),
                            video=Path("/x/f.mp4"), chat_block="",
                            comment_posted=True)
    assert "고정" in summary


def test_요약에_업로드_패키지_블록이_그대로_실린다():
    """038 — 제목·3줄요약·해시태그는 손으로 다시 쓰지 않고 그대로 인용한다."""
    block = "제목: 결국 동결된 금리\n\n3줄요약:\n한 줄\n\n해시태그: #금리"
    assert block in build_summary(slot="noon", decision=Decision(True, ()),
                                  video=None, chat_block=block)


def test_알림은_osascript와_open을_호출한다(tmp_path):
    video = tmp_path / "final.mp4"
    video.write_bytes(b"x")
    calls = []

    notify("제목", "본문", reveal=video, runner=lambda cmd, **kw: calls.append(cmd))
    joined = [" ".join(c) for c in calls]
    assert any("osascript" in c for c in joined)
    assert any(c.startswith("open -R") for c in joined)


def test_알림_실패는_예외를_올리지_않는다():
    """알림이 죽었다고 슬롯을 실패로 만들면 안 된다."""
    def boom(cmd, **kw):
        raise OSError("no osascript")

    notify("제목", "본문", runner=boom)          # 예외 없이 통과해야 한다


def test_없는_파일은_open하지_않는다(tmp_path):
    calls = []
    notify("t", "m", reveal=tmp_path / "없음.mp4",
           runner=lambda cmd, **kw: calls.append(cmd))
    assert not any("open" in c[0] for c in calls)
