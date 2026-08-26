"""039 Phase 2 — 원본 클립 탐색 + 채널 정책 필터 테스트.

037-3: 방송 클립은 화면 자막 카드와 나레이션이 최대 6초까지 어긋난다. 사람이
눈으로 확인하던 그 판단을 무인 운영에서는 **채널 정책 파일**로 대체한다 —
소재와 무관한 카드를 쓰는 채널, 서술이 단정적인 채널을 미리 빼둔다.
"""
import json
import subprocess

import pytest

from scripts.auto_daily.source_finder import (
    ChannelPolicy, SourceCandidate, download_source, load_policy,
    pick_candidates, search_candidates,
)


def _result(stdout="", code=0):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr="")


def _cand(channel="검증채널", dur=600, vid="abc12345678", title="제목"):
    return SourceCandidate(video_id=vid, title=title, channel=channel,
                           duration=dur, url=f"https://www.youtube.com/watch?v={vid}")


# ── 채널 정책 ───────────────────────────────────────────────────────
def test_정책파일을_읽는다(tmp_path):
    path = tmp_path / "channel_policy.json"
    path.write_text(json.dumps({"allow": ["KBS News"], "deny": ["요약채널"]}),
                    encoding="utf-8")
    policy = load_policy(path)
    assert policy.allow == ("KBS News",)
    assert policy.deny == ("요약채널",)


def test_정책파일이_없으면_기본값이고_화이트리스트를_강제한다(tmp_path):
    """등록 안 된 채널을 무인으로 올리면 안 된다 — 없으면 전부 막힌다."""
    policy = load_policy(tmp_path / "missing.json")
    assert policy.require_allowlist is True
    assert policy.is_allowed("아무채널") is False


def test_화이트리스트에_있으면_통과():
    policy = ChannelPolicy(allow=("KBS News",), deny=(), require_allowlist=True)
    assert policy.is_allowed("KBS News") is True


def test_블랙리스트가_화이트리스트를_이긴다():
    policy = ChannelPolicy(allow=("KBS News",), deny=("KBS News",),
                           require_allowlist=True)
    assert policy.is_allowed("KBS News") is False


def test_채널명_부분일치로_판정한다():
    """유튜브 채널명은 'KBS News [뉴스]' 처럼 꼬리가 붙는다."""
    policy = ChannelPolicy(allow=("KBS News",), deny=(), require_allowlist=True)
    assert policy.is_allowed("KBS News 뉴스") is True


def test_화이트리스트_강제를_끄면_블랙리스트만_본다():
    policy = ChannelPolicy(allow=(), deny=("나쁜채널",), require_allowlist=False)
    assert policy.is_allowed("처음보는채널") is True
    assert policy.is_allowed("나쁜채널") is False


def test_빈_채널명은_거부된다():
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    assert policy.is_allowed("") is False


# ── 검색 ────────────────────────────────────────────────────────────
_SEARCH_STDOUT = "\n".join(json.dumps(row, ensure_ascii=False) for row in [
    {"id": "aaaaaaaaaaa", "title": "장동혁 사퇴 기자회견", "channel": "KBS News",
     "duration": 480, "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"},
    {"id": "bbbbbbbbbbb", "title": "오늘의 정치 요약", "channel": "요약채널",
     "duration": 300, "url": "https://www.youtube.com/watch?v=bbbbbbbbbbb"},
])


def test_yt_dlp_검색결과를_파싱한다():
    got = search_candidates("장동혁 사퇴", limit=5,
                            runner=lambda cmd, **kw: _result(_SEARCH_STDOUT))
    assert [c.channel for c in got] == ["KBS News", "요약채널"]
    assert got[0].duration == 480


def test_검색어와_개수가_ytsearch에_들어간다():
    seen = {}

    def runner(cmd, **kw):
        seen["cmd"] = cmd
        return _result(_SEARCH_STDOUT)

    search_candidates("금리 동결", limit=7, runner=runner)
    assert "ytsearch7:금리 동결" in seen["cmd"]


def test_403_대비_EJS_원격컴포넌트를_항상_붙인다():
    """403/포맷없음은 버전이나 player_client 문제가 아니라 챌린지 솔버 부재다."""
    seen = {}

    def runner(cmd, **kw):
        seen["cmd"] = cmd
        return _result(_SEARCH_STDOUT)

    search_candidates("x", runner=runner)
    assert "ejs:github" in seen["cmd"]


def test_검색_실패는_빈리스트():
    assert search_candidates("x", runner=lambda cmd, **kw: _result("", code=1)) == []


def test_깨진_JSON_줄은_건너뛴다():
    stdout = "not json\n" + _SEARCH_STDOUT
    assert len(search_candidates("x", runner=lambda cmd, **kw: _result(stdout))) == 2


def test_yt_dlp가_없으면_빈리스트():
    def runner(cmd, **kw):
        raise FileNotFoundError("yt-dlp")

    assert search_candidates("x", runner=runner) == []


# ── 후보 선별 ───────────────────────────────────────────────────────
def test_허용채널만_남는다():
    policy = ChannelPolicy(allow=("KBS News",), deny=(), require_allowlist=True)
    got = pick_candidates([_cand("KBS News"), _cand("요약채널")], policy)
    assert [c.channel for c in got] == ["KBS News"]


def test_너무_긴_영상은_뺀다():
    """다운로드 시간이 슬롯 예산을 먹는다. config 의 dur_max 와 같은 축."""
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    got = pick_candidates([_cand(dur=5000), _cand(dur=600, vid="ok123456789")],
                          policy, max_duration=900)
    assert [c.video_id for c in got] == ["ok123456789"]


def test_길이를_모르는_영상은_뺀다():
    """라이브·프리미어는 duration 이 없다 — 컷 계획을 세울 수 없다."""
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    assert pick_candidates([_cand(dur=0)], policy) == []


def test_너무_짧은_영상도_뺀다():
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    assert pick_candidates([_cand(dur=15)], policy, min_duration=30) == []


def test_중복_영상은_한_번만():
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    got = pick_candidates([_cand(vid="same1234567"), _cand(vid="same1234567")], policy)
    assert len(got) == 1


def test_상위_N개로_자른다():
    policy = ChannelPolicy(allow=(), deny=(), require_allowlist=False)
    cands = [_cand(vid=f"vid{i:08d}") for i in range(10)]
    assert len(pick_candidates(cands, policy, top_n=3)) == 3


# ── 다운로드 ────────────────────────────────────────────────────────
def test_다운로드_성공시_경로를_돌려준다(tmp_path):
    out = tmp_path / "src_hook.mp4"

    def runner(cmd, **kw):
        out.write_bytes(b"fake")
        return _result()

    assert download_source("https://youtu.be/x", out, runner=runner) == out


def test_다운로드_실패는_None(tmp_path):
    assert download_source("https://youtu.be/x", tmp_path / "a.mp4",
                           runner=lambda cmd, **kw: _result(code=1)) is None


def test_파일이_안생기면_None(tmp_path):
    assert download_source("https://youtu.be/x", tmp_path / "a.mp4",
                           runner=lambda cmd, **kw: _result()) is None


def test_SourceCandidate는_불변이다():
    with pytest.raises(Exception):
        _cand().channel = "다른채널"  # type: ignore[misc]
