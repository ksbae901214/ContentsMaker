"""정치쇼츠 소재 프레임 게이트 (035) — 공방형 대신 '결과가 난 사건'.

근거(채널 실측 2026-08-05): 터진 영상은 전부 결과가 있는 사건이었다
— 7,900회 '5선 오세훈의 13시간 대역전극', 5,600회 '박근혜 9년 침묵의 컴백',
3,048회 '토론장서 터짐'. 반면 'A가 B를 직격/저격' 공방형은 예외 없이
1,100대에 갇혔다 (hook형 중앙값 1,151 = neutral 1,200 과 차이 없음).
"""
from __future__ import annotations

from scripts.political_upload_package import (
    DEFAULT_PINNED_COMMENT, build_upload_package_md, has_outcome_frame,
    is_clash_frame, lint_topic_frame, lint_yt_title, resolve_pinned_comment,
)


# ── 공방형 / 결과형 판정 ────────────────────────────────────────────
class TestFrameDetection:
    def test_clash_verbs_detected(self):
        assert is_clash_frame("장동혁, 조정식 정면 직격") is True
        assert is_clash_frame("여야 정면충돌 공방") is True

    def test_non_clash(self):
        assert is_clash_frame("5선 오세훈의 13시간 대역전극") is False

    def test_outcome_markers_detected(self):
        assert has_outcome_frame("13시간 만에 뒤집힌 표결") is True
        assert has_outcome_frame("9년 침묵 끝에 컴백") is True
        assert has_outcome_frame("결국 사퇴했다") is True

    def test_no_outcome(self):
        assert has_outcome_frame("조국을 저격한 이준석") is False


# ── 소재 프레임 경고 ────────────────────────────────────────────────
class TestLintTopicFrame:
    def test_clash_without_outcome_warns(self):
        warns = lint_topic_frame("장동혁, 조정식 연임 개헌 직격")
        assert any("사건" in w or "결과" in w for w in warns)

    def test_clash_with_outcome_passes(self):
        assert lint_topic_frame("직격 한 방에 결국 철회된 개헌안") == []

    def test_outcome_only_passes(self):
        assert lint_topic_frame("5선 오세훈의 13시간 대역전극") == []

    def test_neutral_title_passes(self):
        assert lint_topic_frame("죽창 들자던 조국, 이젠 말끝으로 사상검증") == []

    def test_wired_into_lint_yt_title(self):
        warns = lint_yt_title("이준석을 정면 저격한 조국 대표", ["조국"])
        assert any("사건" in w or "결과" in w for w in warns)


# ── 고정댓글 (편 가르기) ────────────────────────────────────────────
class TestPinnedComment:
    def test_default_is_side_picking(self):
        from scripts.political_cta import is_side_picking
        assert is_side_picking(DEFAULT_PINNED_COMMENT)

    def test_explicit_pinned_comment_wins(self):
        cfg = {"pinned_comment": "직접 쓴 고정댓글", "cta": {"voice": "① ②"}}
        assert resolve_pinned_comment(cfg) == "직접 쓴 고정댓글"

    def test_falls_back_to_cta_voice(self):
        cfg = {"cta": {"voice": "이건 누구 잘못일까요? 1번, 2번 댓글로."}}
        assert resolve_pinned_comment(cfg) == "이건 누구 잘못일까요? 1번, 2번 댓글로."

    def test_falls_back_to_default(self):
        assert resolve_pinned_comment({}) == DEFAULT_PINNED_COMMENT

    def test_package_uses_cta_voice(self, tmp_path):
        cfg = {
            "slug": "s", "title": "t", "yt_title": "죽창 들자던 조국, 말끝으로 사상검증",
            "persons": ["조국"],
            "cta": {"voice": "누구 잘못일까요? ① 조국 ② 이준석"},
        }
        md = build_upload_package_md(cfg, tmp_path / "v.mp4",
                                     suggested=__import__("datetime").datetime(2026, 8, 5, 20, 0))
        assert "누구 잘못일까요? ① 조국 ② 이준석" in md


# ── 업로드 체크리스트 (035 항목 추가) ───────────────────────────────
class TestChecklist:
    def _md(self, tmp_path):
        cfg = {"slug": "s", "title": "t", "yt_title": "죽창 들자던 조국, 말끝으로 사상검증",
               "persons": ["조국"]}
        return build_upload_package_md(
            cfg, tmp_path / "v.mp4",
            suggested=__import__("datetime").datetime(2026, 8, 5, 20, 0))

    def test_keeps_034_items(self, tmp_path):
        md = self._md(tmp_path)
        assert "체크리스트" in md
        assert "플랫폼 분리" in md

    def test_has_length_item(self, tmp_path):
        assert "42초" in self._md(tmp_path)

    def test_has_midroll_cta_item(self, tmp_path):
        md = self._md(tmp_path)
        assert "40%" in md and "댓글" in md
