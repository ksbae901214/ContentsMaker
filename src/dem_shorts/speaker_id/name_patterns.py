"""T047: 자막 호명 패턴 → 화자 후보 추출 (FR-013 MVP).

전략 (research.md R-04):
  - MVP: 정규식 기반 이름+역할 매칭만 (정확도 60~70% 목표)
  - Sprint 2+: OCR(이름표) + 출석자 명단 결합 (80%+)

본 모듈은 MVP 계층만 구현.
"""
from __future__ import annotations

import re

# 한글 2~4글자 + (의원|대표|장관|위원장|부총리|총리)
# 2글자도 일단 매칭하되 extract_named_speakers()에서 3글자 이상만 확정.
NAME_ROLE_RE = re.compile(
    r"(?P<name>[가-힣]{2,4})\s*(?P<role>의원|대표|장관|위원장|부총리|총리)"
)


def extract_named_speakers(text: str) -> set[str]:
    """텍스트에서 `이름 + 역할명` 패턴을 발견해 이름 집합을 반환.

    - 2글자 이름은 제외 (노이즈 많음: "그 분" 등)
    - 중복 제거
    """
    names: set[str] = set()
    for m in NAME_ROLE_RE.finditer(text):
        name = m.group("name")
        if len(name) < 3:
            continue
        names.add(name)
    return names


def match_whitelist(names: set[str], whitelist: list[dict]) -> dict[str, int]:
    """이름 집합을 Whitelist와 매칭.

    Args:
        names: extract_named_speakers()의 반환값
        whitelist: DB에서 가져온 [{id, name, tier, is_active, ...}] dict 리스트

    Returns:
        {이름: politician_id} — 활성이고 blocked가 아닌 인물만 포함.
    """
    name_to_id: dict[str, int] = {}
    for p in whitelist:
        if not p.get("is_active", True):
            continue
        if p.get("tier") == "blocked":
            continue
        if p["name"] in names:
            name_to_id[p["name"]] = p["id"]
    return name_to_id
