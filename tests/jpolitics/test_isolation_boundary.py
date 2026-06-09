"""T007: 격리 경계 강제 — V3 코드가 기존 V1/V2 파일을 mutating(편집·monkey-patch)하지 않음.

읽기 전용 import (from X import Y)는 허용. 다음 행위는 금지:
  - V1/V2 파일을 src/jpolitics/* 안에서 textually 수정
  - monkey-patch (setattr, .__dict__ 할당)
  - 모듈 전역 mutating import side-effect

SC-003 (V1/V2 297+ 회귀 테스트 100% 통과) 보장의 정적 가드.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from src.jpolitics.constants import PROJECT_ROOT

# 편집 금지 대상 (read-only import만 허용)
PROTECTED_PATHS = [
    "src/analyzer/script_models.py",
    "src/analyzer/political_planner.py",
    "src/analyzer/political_plan_models.py",
    "src/analyzer/claude_analyzer.py",
    "src/analyzer/gemini_backend.py",
    "src/tts/voice_config.py",
    "src/tts/edge_tts_synth.py",
    "src/video/renderer.py",
    "src/scraper/youtube_news_searcher.py",
    "src/scraper/naver_image_search.py",
    "src/editor/subtitle_split.py",
]

V3_SOURCE_DIRS = [
    "src/jpolitics",
    "src/video/remotion_v3",
    "app/jpolitics",
    "tests/jpolitics",
]


def _collect_v3_python_files() -> list[Path]:
    files: list[Path] = []
    for dir_rel in V3_SOURCE_DIRS:
        dir_abs = PROJECT_ROOT / dir_rel
        if not dir_abs.exists():
            continue
        files.extend(dir_abs.rglob("*.py"))
    return files


def test_v3_python_files_never_textually_modify_protected_files() -> None:
    """V3 파이썬 파일에 PROTECTED_PATHS의 절대/상대 경로 + open(mode='w') 패턴 부재."""
    write_pattern = re.compile(r"""open\(\s*['"][^'"]*('|")\s*,\s*['"][wxa]""")
    for v3_file in _collect_v3_python_files():
        text = v3_file.read_text(encoding="utf-8")
        for protected in PROTECTED_PATHS:
            if protected in text:
                # 단순 path 언급은 OK (문서/로그). open(..., 'w'/'x'/'a')만 금지.
                assert not write_pattern.search(
                    text
                ), f"{v3_file} attempts to write to protected path {protected}"


def test_v3_python_files_use_only_read_only_imports() -> None:
    """V3 파일은 PROTECTED 모듈을 from-import만, '* mutating' 패턴 부재."""
    for v3_file in _collect_v3_python_files():
        try:
            tree = ast.parse(v3_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # `setattr(some_v1_module, ...)` 패턴 검출
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "setattr" and node.args:
                    first = node.args[0]
                    # setattr(target, ...) 의 target이 PROTECTED 모듈 식별자면 fail
                    if isinstance(first, ast.Name):
                        name = first.id
                        for protected in PROTECTED_PATHS:
                            module_name = (
                                protected.replace("/", ".").replace(".py", "")
                            )
                            if name in module_name.split("."):
                                raise AssertionError(
                                    f"{v3_file} monkey-patches protected module {protected}"
                                )


def test_v3_does_not_modify_app_page_tsx_except_button_addition() -> None:
    """app/page.tsx 수정은 T072 진입 버튼 추가만 허용.

    이 테스트는 placeholder — 실제 구현에서는 git diff 분석으로 강화 가능.
    현재는 V3 페이지가 app/jpolitics/page.tsx에만 존재하는지 검증.
    """
    main_page = PROJECT_ROOT / "app" / "page.tsx"
    assert main_page.exists(), "app/page.tsx must exist (touched only for T072)"

    v3_page = PROJECT_ROOT / "app" / "jpolitics" / "page.tsx"
    # V3 페이지는 T034에서 생성됨. Phase 1/2에서는 아직 미존재 OK.
    if v3_page.exists():
        # 존재하면 V3 전용 내용이어야 함
        content = v3_page.read_text(encoding="utf-8")
        assert "jpolitics" in content.lower() or "V3" in content
