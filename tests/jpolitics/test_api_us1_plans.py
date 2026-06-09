"""T015 [US1]: Next.js API 라우트 contract test — `/api/jpolitics/plans` 입출력 스키마.

이 테스트는 Python에서 API 응답 JSON 구조만 검증 (Next.js 런타임 없이).
실제 HTTP 테스트는 e2e에서. 여기는 contracts/api.md 스키마 정합성만.

RED 상태 — T037 구현 후 GREEN.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_contracts_api_md_documents_jpolitics_plans_endpoint() -> None:
    """contracts/api.md에 `/api/jpolitics/plans` 명세 존재."""
    from src.jpolitics.constants import PROJECT_ROOT

    api_md = PROJECT_ROOT / "specs" / "010-jpolitics-v3-isolated" / "contracts" / "api.md"
    assert api_md.exists()
    content = api_md.read_text()
    assert "/api/jpolitics/plans" in content
    assert "sourceType" in content
    assert "youtubeUrl" in content or "youtube_url" in content


def test_api_plans_route_file_exists_after_t037() -> None:
    """T037 구현 후 app/jpolitics/api/plans/route.ts 존재.

    Phase 1/2에서는 파일이 없으므로 xfail 표시 가능 — 여기는 가이드.
    """
    from src.jpolitics.constants import PROJECT_ROOT

    route_file = PROJECT_ROOT / "app" / "jpolitics" / "api" / "plans" / "route.ts"
    # T037 구현 전에는 미존재 — pytest.skip 대신 마커로 표시
    if not route_file.exists():
        pytest.xfail("T037 not yet implemented")
    content = route_file.read_text()
    assert "POST" in content
    assert "jpolitics" in content.lower()


def test_request_body_youtube_mode_schema_documented() -> None:
    """contracts/api.md에 YouTube 모드 request body 스키마 문서화."""
    from src.jpolitics.constants import PROJECT_ROOT

    api_md = PROJECT_ROOT / "specs" / "010-jpolitics-v3-isolated" / "contracts" / "api.md"
    content = api_md.read_text()
    # YouTube 모드 예시에 sourceType + youtubeUrl 키 포함
    yt_block = content[content.find("YouTube 모드") : content.find("Topic 모드")]
    assert '"sourceType"' in yt_block
    assert '"youtubeUrl"' in yt_block


def test_request_body_topic_mode_schema_documented() -> None:
    """contracts/api.md에 Topic 모드 request body 스키마 문서화."""
    from src.jpolitics.constants import PROJECT_ROOT

    api_md = PROJECT_ROOT / "specs" / "010-jpolitics-v3-isolated" / "contracts" / "api.md"
    content = api_md.read_text()
    topic_block = content[content.find("Topic 모드") :]
    assert '"topic"' in topic_block
    assert '"tone"' in topic_block
