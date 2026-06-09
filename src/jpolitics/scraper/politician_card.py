"""T045/T046 [US2]: 인물 카드 페치 (Naver 이미지 검색) + infer_party (Claude).

US2 단계에서 활성:
- fetch_politician_card(name): 캐시 → Naver 이미지 검색 → 다운로드 → 캐시 저장
- infer_party(name): Claude 1-shot 호출로 정당 추론 (party=None일 때만)
- get_party_color(party): PARTY_COLORS 매핑 + 미매핑 #888 폴백 (FR-028)

Read-only import (격리 boundary):
- src.illustrator.naver_image_search.NaverImageSearcher
- src.analyzer.claude_analyzer._call_claude
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Read-only imports — 격리 boundary, 편집 금지
from src.analyzer.claude_analyzer import _call_claude  # noqa: F401
from src.illustrator.naver_image_search import (  # noqa: F401
    NaverImageSearcher,
    NaverImageSearchError,
)

from src.jpolitics.constants import (
    DEFAULT_PARTY_COLOR,
    PARTY_COLORS,
    POLITICIAN_CARDS_DIR,
    POLITICIAN_PHOTOS_DIR,
)
from src.jpolitics.logger import get_logger
from src.jpolitics.models.politician_card import PoliticianCard

logger = get_logger("scraper.politician_card")


# ─────────────────────────── 정당 컬러 ───────────────────────────


def get_party_color(party: str) -> str:
    """정당명 → 헥스 컬러. 미매핑 시 회색(#888) 폴백 + 경고 로그 (FR-028)."""
    color = PARTY_COLORS.get(party)
    if color is None:
        logger.warning("Party '%s' not in PARTY_COLORS, using default #888", party)
        return DEFAULT_PARTY_COLOR
    return color


# ─────────────────────────── 캐시 ───────────────────────────


def _cache_path(name: str) -> Path:
    safe = name.replace("/", "_").replace("\\", "_")
    return POLITICIAN_CARDS_DIR / f"{safe}.json"


def load_cached_card(name: str) -> PoliticianCard | None:
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return PoliticianCard.from_dict(data)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Cache for %s corrupted: %s", name, e)
        return None


def save_cached_card(card: PoliticianCard) -> None:
    POLITICIAN_CARDS_DIR.mkdir(parents=True, exist_ok=True)
    p = _cache_path(card.name)
    p.write_text(
        json.dumps(card.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─────────────────────────── infer_party (Claude) ───────────────────────────


def _normalize_party_response(text: str) -> str:
    """Claude 응답을 PARTY_COLORS 키 후보로 정규화.

    개행/공백/문장부호 제거 후 첫 줄만 사용.
    """
    # 첫 줄
    first_line = text.strip().split("\n", 1)[0].strip()
    # 양 끝의 일반 문장부호 제거
    cleaned = first_line.strip(" .。,，!?\"'`()[]{}")
    # 내부 공백 제거 (정당명은 한 단어)
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned


def infer_party(name: str) -> str:
    """정치인 이름 → 소속 정당명 (Claude 1-shot).

    응답이 PARTY_COLORS 키와 매칭되면 그대로, 아니면 "기타" + 경고 로그.
    """
    allowed = list(PARTY_COLORS.keys())
    prompt = (
        f"정치인 '{name}'의 현재 소속 정당명만 정확히 한 줄로 출력하세요.\n"
        f"무소속이면 '무소속'으로 출력. 다음 중 하나여야 합니다: {allowed}\n"
        f"오직 정당명 한 단어만 출력하고 다른 설명은 포함하지 마세요."
    )
    try:
        raw = _call_claude(prompt)
    except Exception as e:  # noqa: BLE001
        logger.warning("infer_party Claude call failed for %s: %s", name, e)
        return "기타"

    normalized = _normalize_party_response(raw)
    if normalized in PARTY_COLORS:
        return normalized
    logger.warning(
        "infer_party for '%s' returned unmapped value %r → '기타'",
        name,
        normalized,
    )
    return "기타"


# ─────────────────────────── Naver 이미지 검색 ───────────────────────────


def _safe_filename(name: str) -> str:
    """name → 안전한 파일명 (한글 보존, 슬래시 등 제거)."""
    return re.sub(r"[\\/:*?\"<>|]", "_", name)


def _naver_fetch_photo(name: str) -> str | None:
    """Naver 이미지 검색으로 정면 사진 1장 다운로드 → 로컬 경로 반환.

    실패 시 None 반환 (검색 실패 / 다운로드 실패 / 환경변수 미설정 모두 처리).
    """
    POLITICIAN_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    queries = [f"{name} 의원", f"{name} 정치인", name]

    searcher: NaverImageSearcher | None = None
    try:
        searcher = NaverImageSearcher()
        for q in queries:
            try:
                hits = searcher.search(q, count=1, sort="sim")
            except NaverImageSearchError as e:
                logger.warning("Naver search for '%s' failed: %s", q, e)
                continue
            if not hits:
                continue
            try:
                saved = searcher.download(
                    hits,
                    output_dir=POLITICIAN_PHOTOS_DIR,
                    filename_prefix=_safe_filename(name),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Photo download failed for '%s': %s", name, e)
                continue
            if not saved:
                continue
            return str(saved[0])
        return None
    except NaverImageSearchError as e:
        # 환경변수 미설정 등 초기화 단계 에러
        logger.warning("Naver searcher init failed for '%s': %s", name, e)
        return None
    finally:
        if searcher is not None:
            try:
                searcher.close()
            except Exception:  # noqa: BLE001
                pass


# ─────────────────────────── fetch_politician_card ───────────────────────────


def fetch_politician_card(
    name: str,
    *,
    party: str | None = None,
    data_label: str | None = None,
    data_value: str | None = None,
) -> PoliticianCard:
    """인물 카드 페치 (캐시 우선 → Naver 이미지 검색).

    흐름:
        1. 캐시 히트 + data_label 미지정 → 즉시 반환 (SC-005).
        2. 캐시 미스 → party 미지정 시 infer_party 호출.
        3. Naver 이미지 검색 + 다운로드 (실패 시 photo_path=None).
        4. PoliticianCard 생성 + 캐시 저장.

    Args:
        name: 정치인 이름.
        party: 정당명 (None이면 캐시 또는 infer_party 호출).
        data_label/data_value: 데이터 카드용 (grid_2x2 / data_card).
    """
    cached = load_cached_card(name)
    if cached is not None and not data_label:
        return cached

    # 정당 결정: 인자 → 캐시 → Claude infer
    if party is not None:
        resolved_party = party
    elif cached is not None:
        resolved_party = cached.party
    else:
        resolved_party = infer_party(name)

    # 사진 결정: 캐시 → Naver
    if cached is not None and cached.photo_path:
        photo_path = cached.photo_path
    else:
        photo_path = _naver_fetch_photo(name)
        if photo_path is None:
            logger.warning(
                "No photo found for '%s' — falling back to silhouette (FR-027)", name
            )

    card = PoliticianCard(
        name=name,
        party=resolved_party,
        party_color=get_party_color(resolved_party),
        photo_path=photo_path,
        data_label=data_label,
        data_value=data_value,
    )

    # 캐시는 사진 + 정당 핵심 정보만 저장 (data_label/value는 씬마다 다르므로 제외)
    save_cached_card(
        PoliticianCard(
            name=name,
            party=resolved_party,
            party_color=card.party_color,
            photo_path=photo_path,
        )
    )
    return card
