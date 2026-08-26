"""039 Phase 5 — launchd 스케줄 설치기 테스트."""
import plistlib

import pytest

from scripts.auto_daily.launchd import LABEL_PREFIX, install, plist_bytes
from scripts.auto_daily.slots import SLOT_NAMES, slot_for_name


def _parsed(slot_name="morning", **kw):
    return plistlib.loads(plist_bytes(slot_for_name(slot_name), **kw))


def test_슬롯_시각이_StartCalendarInterval에_들어간다():
    for name, hour in (("morning", 7), ("noon", 12), ("evening", 18)):
        assert _parsed(name)["StartCalendarInterval"]["Hour"] == hour
        assert _parsed(name)["StartCalendarInterval"]["Minute"] == 0


def test_라벨은_슬롯마다_다르다():
    labels = {_parsed(n)["Label"] for n in SLOT_NAMES}
    assert len(labels) == len(SLOT_NAMES)
    assert all(x.startswith(LABEL_PREFIX) for x in labels)


def test_실행인자에_슬롯이름이_들어간다():
    args = _parsed("noon")["ProgramArguments"]
    assert "--slot" in args and "noon" in args
    assert "scripts.auto_daily.runner" in args


def test_프로젝트_경로가_하드코딩되지_않는다(tmp_path):
    """기존 daily-briefing plist 는 /Users/kyusik 이 박혀 있어 못 쓴다."""
    parsed = _parsed("morning", project_root=tmp_path, python_bin="/py")
    assert parsed["WorkingDirectory"] == str(tmp_path)
    assert parsed["ProgramArguments"][0] == "/py"
    assert parsed["EnvironmentVariables"]["PYTHONPATH"] == str(tmp_path)


def test_로그_경로가_슬롯별로_갈린다():
    out = _parsed("morning")["StandardOutPath"]
    err = _parsed("morning")["StandardErrorPath"]
    assert "morning" in out and out != err


def test_잠들어_있다_깨면_실행되도록_한다():
    """맥이 슬립이면 놓친다 — 깬 뒤라도 돌게 해야 그날 편수가 유지된다."""
    assert _parsed("morning")["RunAtLoad"] is False
    assert _parsed("morning")["StartCalendarInterval"]["Hour"] == 7


def test_환경변수를_주입할_수_있다():
    parsed = _parsed("morning", env={"GEMINI_API_KEY": "k"})
    assert parsed["EnvironmentVariables"]["GEMINI_API_KEY"] == "k"


def test_PATH가_들어간다():
    """launchd 는 로그인 셸 PATH 를 물려받지 않는다 — ffmpeg/yt-dlp 를 못 찾는다."""
    assert "PATH" in _parsed("morning")["EnvironmentVariables"]


def test_세_슬롯을_설치한다(tmp_path):
    written = install(out_dir=tmp_path, project_root=tmp_path, python_bin="/py")
    assert len(written) == 3
    assert all(p.exists() for p in written)
    assert {p.name for p in written} == {
        f"{LABEL_PREFIX}{n}.plist" for n in SLOT_NAMES}


def test_설치는_기존파일을_덮어쓴다(tmp_path):
    install(out_dir=tmp_path, project_root=tmp_path, python_bin="/py")
    written = install(out_dir=tmp_path, project_root=tmp_path, python_bin="/py2")
    assert plistlib.loads(written[0].read_bytes())["ProgramArguments"][0] == "/py2"


def test_설치된_plist가_유효한_형식이다(tmp_path):
    for path in install(out_dir=tmp_path, project_root=tmp_path, python_bin="/py"):
        assert plistlib.loads(path.read_bytes())["Label"]


def test_알수없는_슬롯은_ValueError():
    with pytest.raises(ValueError):
        slot_for_name("midnight")
