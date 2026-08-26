"""039 Phase 5 — 슬롯 오케스트레이션 테스트.

바깥 세계(네이버·yt-dlp·Claude·Remotion·업로드)는 전부 주입한다.
검증 대상은 **분기와 실패 격리**다 — 한 단계가 죽어도 사유가 남고 다음 슬롯이
살아 있어야 한다.
"""
import json
import subprocess
from datetime import datetime

import pytest

from scripts.auto_daily.cut_planner import Cut
from scripts.auto_daily.naver_metrics import Article
from scripts.auto_daily.review_gate import GatePolicy
from scripts.auto_daily.runner import Deps, SlotResult, run_slot, slot_lock
from scripts.auto_daily.slots import KST
from scripts.auto_daily.source_finder import SourceCandidate
from scripts.auto_daily.topic_ranker import TopicCluster

NOW = datetime(2026, 8, 26, 7, 0, tzinfo=KST)
CAND = SourceCandidate(video_id="abc12345678", title="기자회견", channel="KBS News",
                       duration=600, url="https://www.youtube.com/watch?v=abc12345678")
CUTS = [Cut(0.0, 4.0, "저는 사퇴하지 않습니다")]


def _topic(anchor="장동혁"):
    art = Article(title=f"{anchor} 대표직 사퇴",
                  link="https://n.news.naver.com/mnews/article/001/0000000001",
                  metric=900)
    return TopicCluster(anchor=anchor, articles=(art,), total_metric=900,
                        has_outcome=True, warnings=())


def _cfg():
    return {"category": "political", "slug": "s", "title": "t",
            "sources": {"main": {"query": "q"}},
            "scenes": [{"mode": "clip", "source": "main", "duration": 9.0},
                       {"mode": "tts", "source": "main", "voice": "가" * 20}]}


def _deps(tmp_path, **over):
    published = over.pop("_published", [])
    base = dict(
        collect_topics=lambda slot, now: [_topic()],
        find_candidates=lambda slot, topic: [CAND],
        plan_cuts=lambda candidate, work_dir, key: CUTS,
        draft=lambda topic, candidate, cuts, category, slug: _Draft(_cfg()),
        render=lambda config_path, work_dir: tmp_path / "final.mp4",
        chat_block=lambda cfg: "제목: 사퇴",
        publish=lambda video, cfg, slug: published.append(video) or _Outcome(),
        notifier=lambda title, message, reveal=None: None,
        gate_policy=GatePolicy(always_hold=False, max_warnings=0),
    )
    base.update(over)
    return Deps(**base)


class _Draft:
    def __init__(self, config, ok=True, errors=(), warnings=()):
        self.config, self.ok = config, ok
        self.errors, self.warnings = tuple(errors), tuple(warnings)
        self.attempts = 1


class _Outcome:
    youtube_url = "https://youtu.be/abc12345678"
    tiktok_publish_id = "pid"
    comment_id = "cid"
    errors: tuple = ()
    tiktok_needs_manual_publish = True
    comment_needs_manual_pin = True


# ── 정상 경로 ───────────────────────────────────────────────────────
def test_전체_경로가_돌면_게시된다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    published = []
    result = run_slot("morning", now=NOW, root=tmp_path,
                      deps=_deps(tmp_path, _published=published))
    assert result.status == "published"
    assert published


def test_topics_json이_남는다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    result = run_slot("morning", now=NOW, root=tmp_path, deps=_deps(tmp_path))
    assert (result.work_dir / "topics.json").exists()


def test_config가_파일로_저장된다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    result = run_slot("morning", now=NOW, root=tmp_path, deps=_deps(tmp_path))
    saved = json.loads((result.work_dir / "config.json").read_text(encoding="utf-8"))
    assert saved["slug"] == result.config["slug"]


def test_드래프터에_날짜와_소재가_담긴_슬러그를_넘긴다(tmp_path):
    """slug 는 런너가 정하고 drafter 가 강제 주입한다 — LLM 이 정하면 산출물이 샌다."""
    (tmp_path / "final.mp4").write_bytes(b"x")
    seen = {}

    def draft(topic, candidate, cuts, category, slug):
        seen["slug"] = slug
        return _Draft(_cfg())

    run_slot("morning", now=NOW, root=tmp_path, deps=_deps(tmp_path, draft=draft))
    assert seen["slug"].startswith("20260826_장동혁")
    assert seen["slug"].endswith("_v2_2")


# ── 보류 ────────────────────────────────────────────────────────────
def test_전면보류면_업로드를_호출하지_않는다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    published = []
    deps = _deps(tmp_path, _published=published,
                 gate_policy=GatePolicy(always_hold=True))
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert result.status == "held"
    assert published == []


def test_게이트_경고가_있으면_보류한다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    deps = _deps(tmp_path,
                 draft=lambda *a, **kw: _Draft(_cfg(), warnings=("길이 초과",)))
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert result.status == "held"
    assert any("길이 초과" in r for r in result.reasons)


def test_보류여도_알림은_간다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    sent = []
    deps = _deps(tmp_path, gate_policy=GatePolicy(always_hold=True),
                 notifier=lambda title, message, reveal=None: sent.append(message))
    run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert sent and "보류" in sent[0]


# ── 실패 격리 ───────────────────────────────────────────────────────
def test_소재가_없으면_실패로_끝난다(tmp_path):
    result = run_slot("morning", now=NOW, root=tmp_path,
                      deps=_deps(tmp_path, collect_topics=lambda slot, now: []))
    assert result.status == "failed"
    assert any("소재" in r for r in result.reasons)


def test_허용채널_후보가_없으면_실패한다(tmp_path):
    deps = _deps(tmp_path, find_candidates=lambda slot, topic: [])
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert result.status == "failed"


def test_첫_소재가_실패하면_다음_소재로_넘어간다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    tried = []

    def draft(topic, candidate, cuts, category, slug):
        tried.append(topic.anchor)
        return _Draft(_cfg()) if topic.anchor == "두번째" else _Draft(None, ok=False)

    deps = _deps(tmp_path, draft=draft,
                 collect_topics=lambda slot, now: [_topic("첫번째"), _topic("두번째")])
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert tried == ["첫번째", "두번째"]
    assert result.status == "published"


def test_컷을_못_뽑으면_다음_후보로_넘어간다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    other = SourceCandidate(video_id="zzz11111111", title="다른 클립",
                            channel="KBS News", duration=500,
                            url="https://www.youtube.com/watch?v=zzz11111111")
    used = []

    def plan_cuts(candidate, work_dir, key):
        used.append(candidate.video_id)
        return [] if candidate.video_id == "abc12345678" else CUTS

    deps = _deps(tmp_path, plan_cuts=plan_cuts,
                 find_candidates=lambda slot, topic: [CAND, other])
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert used == ["abc12345678", "zzz11111111"]
    assert result.status == "published"


def test_렌더_실패는_실패로_남는다(tmp_path):
    deps = _deps(tmp_path, render=lambda config_path, work_dir: None)
    result = run_slot("morning", now=NOW, root=tmp_path, deps=deps)
    assert result.status == "failed"
    assert any("렌더" in r for r in result.reasons)


def test_업로드_예외는_삼키고_사유로_남는다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")

    def boom(video, cfg, slug):
        raise RuntimeError("quota exceeded")

    result = run_slot("morning", now=NOW, root=tmp_path,
                      deps=_deps(tmp_path, publish=boom))
    assert result.status == "failed"
    assert any("quota" in r for r in result.reasons)


def test_알_수_없는_슬롯은_ValueError(tmp_path):
    with pytest.raises(ValueError):
        run_slot("midnight", now=NOW, root=tmp_path, deps=_deps(tmp_path))


# ── 중복 실행 방지 ──────────────────────────────────────────────────
def test_락이_잡혀_있으면_건너뛴다(tmp_path):
    (tmp_path / "final.mp4").write_bytes(b"x")
    with slot_lock("morning", root=tmp_path):
        result = run_slot("morning", now=NOW, root=tmp_path, deps=_deps(tmp_path))
    assert result.status == "skipped"


def test_락은_끝나면_풀린다(tmp_path):
    with slot_lock("morning", root=tmp_path):
        pass
    with slot_lock("morning", root=tmp_path) as acquired:
        assert acquired is True


def test_예외가_나도_락은_풀린다(tmp_path):
    with pytest.raises(RuntimeError):
        with slot_lock("morning", root=tmp_path):
            raise RuntimeError("boom")
    with slot_lock("morning", root=tmp_path) as acquired:
        assert acquired is True


def test_SlotResult는_불변이다(tmp_path):
    r = SlotResult(slot="morning", status="failed", reasons=(), config=None,
                   video=None, work_dir=tmp_path)
    with pytest.raises(Exception):
        r.status = "published"  # type: ignore[misc]


# ── 렌더러 연동 ─────────────────────────────────────────────────────
def test_렌더_산출물은_stdout_마지막줄에서_읽는다(tmp_path):
    """산출물은 work_dir 이 아니라 data/political_pro/{slug}/ 에 생긴다.

    경로 규칙을 런너에 복제하면 렌더러가 바뀔 때 조용히 어긋난다.
    """
    from scripts.auto_daily.runner import _default_render

    mp4 = tmp_path / "political_pro_out.mp4"
    mp4.write_bytes(b"x")
    stages = []

    def runner(cmd, **kw):
        stages.append(cmd[-1])
        return subprocess.CompletedProcess(
            cmd, 0, stdout=f"진행 로그\n📁 출력: {mp4}\n{mp4}\n", stderr="")

    assert _default_render(tmp_path / "config.json", tmp_path, runner=runner) == mp4
    assert stages == ["download", "render"]


def test_download가_실패하면_render를_돌리지_않는다(tmp_path):
    from scripts.auto_daily.runner import _default_render

    stages = []

    def runner(cmd, **kw):
        stages.append(cmd[-1])
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="소스 없음")

    assert _default_render(tmp_path / "c.json", tmp_path, runner=runner) is None
    assert stages == ["download"]


def test_stdout에_실재하는_mp4가_없으면_None(tmp_path):
    from scripts.auto_daily.runner import _default_render

    def runner(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="/없는/경로.mp4\n", stderr="")

    assert _default_render(tmp_path / "c.json", tmp_path, runner=runner) is None
