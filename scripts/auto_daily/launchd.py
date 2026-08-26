"""039 Phase 5 — launchd 스케줄 설치기 (07:00 / 12:00 / 18:00 KST).

    PYTHONPATH=. .venv311/bin/python -m scripts.auto_daily.launchd --install
    launchctl load ~/Library/LaunchAgents/com.contentsmaker.auto-daily-morning.plist

기존 `com.contentsmaker.daily-briefing.plist` 는 `/Users/kyusik` 이 하드코딩돼
있어 그대로 못 쓴다. 그래서 파일을 손으로 3벌 두는 대신 실행 환경에서 경로를
읽어 생성한다.

**주의 — launchd 는 로그인 셸의 PATH 를 물려받지 않는다.** PATH 를 명시하지
않으면 `ffmpeg`/`yt-dlp` 를 못 찾아 렌더가 조용히 실패한다.
"""
from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path

from scripts.auto_daily.slots import SlotSpec, all_slots

from src.config.settings import PROJECT_ROOT

LABEL_PREFIX = "com.contentsmaker.auto-daily-"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
#: Homebrew(Apple Silicon/Intel) + 시스템 경로. ffmpeg·yt-dlp·node 가 여기 있다.
DEFAULT_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

#: 슬롯 실행에 필요한 키. 값은 설치 시점 환경에서 읽어 넣는다(파일에 안 박는다).
PASSTHROUGH_ENV = (
    "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "YOUTUBE_API_KEY",
)


def plist_bytes(slot: SlotSpec, *, project_root: Path | None = None,
                python_bin: str | None = None,
                env: dict[str, str] | None = None) -> bytes:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    log_dir = root / "data" / "auto_daily"
    environment = {
        "PATH": DEFAULT_PATH,
        "PYTHONPATH": str(root),
        **(env or {}),
    }
    payload = {
        "Label": f"{LABEL_PREFIX}{slot.name}",
        "ProgramArguments": [
            python_bin or sys.executable,
            "-m", "scripts.auto_daily.runner",
            "--slot", slot.name,
        ],
        "WorkingDirectory": str(root),
        "EnvironmentVariables": environment,
        "StartCalendarInterval": {"Hour": slot.hour, "Minute": 0},
        # 로드할 때마다 즉시 돌면 안 된다 — 재부팅 때 세 편이 한꺼번에 나간다.
        "RunAtLoad": False,
        "StandardOutPath": str(log_dir / f".{slot.name}.log"),
        "StandardErrorPath": str(log_dir / f".{slot.name}.err.log"),
        "AbandonProcessGroup": False,
    }
    return plistlib.dumps(payload)


def install(*, out_dir: Path | None = None, project_root: Path | None = None,
            python_bin: str | None = None,
            env: dict[str, str] | None = None) -> list[Path]:
    """세 슬롯의 plist 를 쓰고 경로 목록을 돌려준다. 기존 파일은 덮어쓴다."""
    target = Path(out_dir) if out_dir is not None else LAUNCH_AGENTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    written = []
    for slot in all_slots():
        path = target / f"{LABEL_PREFIX}{slot.name}.plist"
        path.write_bytes(plist_bytes(slot, project_root=project_root,
                                     python_bin=python_bin, env=env))
        written.append(path)
    return written


def _env_from_process() -> dict[str, str]:
    import os
    return {k: os.environ[k] for k in PASSTHROUGH_ENV if os.environ.get(k)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="039 자동 슬롯 launchd 설치")
    parser.add_argument("--install", action="store_true",
                        help="~/Library/LaunchAgents 에 plist 3개 생성")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    if not args.install:
        for slot in all_slots():
            print(plist_bytes(slot).decode("utf-8"))
        return 0

    written = install(out_dir=Path(args.out_dir) if args.out_dir else None,
                      env=_env_from_process())
    print("생성됨:")
    for path in written:
        print(f"  {path}")
    print("\n활성화:")
    for path in written:
        print(f"  launchctl load {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
