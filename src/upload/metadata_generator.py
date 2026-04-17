"""Auto-generate YouTube metadata from ShortsScript.

Generates title, description, and tags for YouTube upload.
"""
from __future__ import annotations

from src.analyzer.script_models import ShortsScript

EMOTION_HASHTAGS = {
    "funny": ["#블라인드", "#직장인", "#웃긴이야기", "#쇼츠", "#shorts"],
    "touching": ["#블라인드", "#직장인", "#감동", "#공감", "#shorts"],
    "angry": ["#블라인드", "#직장인", "#현실", "#분노", "#shorts"],
    "relatable": ["#블라인드", "#직장인", "#공감", "#일상", "#shorts"],
}

# QW-08 클릭베이트 가드: YouTube 정책/계정 정지 리스크 차단용 금칙어 → 사실형 대체어
# 매치 시 description 은 대체, title 은 사실 기반 fallback 으로 재생성한다.
BANNED_CLICKBAIT_WORDS: dict[str, str] = {
    "믿을 수 없는": "주목받은",
    "충격적": "주목할",
    "충격": "주요",
    "경악": "놀라운",
    "폭로": "공개",
    "완벽한": "주요",
    "반드시": "예정된",
    "절대": "주요",
    "결국": "최종",
    "100%": "확정",
}


_HASHTAG_KEYWORD_MAX_COUNT = 10
_HASHTAG_TOTAL_MAX_COUNT = 15
_PURE_NUMBER_RE = None  # lazy compiled in _is_meaningful_keyword


def _is_meaningful_keyword(word: str) -> bool:
    """해시태그 후보 검증 — 의미 있는 키워드만 통과."""
    import re
    cleaned = re.sub(r"[\s\W_]+", "", word)
    if len(cleaned) < 2:
        return False
    if cleaned.isdigit():
        return False
    return True


def _to_hashtag(word: str) -> str:
    """공백/특수문자 제거 후 # prefix."""
    import re
    cleaned = re.sub(r"[\s\W_]+", "", word)
    return f"#{cleaned}"


def extract_keyword_hashtags(script: ShortsScript) -> list[str]:
    """MID-08: 모든 씬의 highlight_words에서 해시태그를 추출.

    - 1글자/순수 숫자 키워드는 제외
    - 공백·특수문자 제거 후 # prefix
    - dedupe (등장 순서 보존)
    - 최대 10개로 제한 (해시태그 스팸 방지)
    """
    tags: list[str] = []
    seen: set[str] = set()
    for scene in script.scenes:
        for word in scene.highlight_words or ():
            if not _is_meaningful_keyword(word):
                continue
            tag = _to_hashtag(word)
            if tag in seen:
                continue
            seen.add(tag)
            tags.append(tag)
            if len(tags) >= _HASHTAG_KEYWORD_MAX_COUNT:
                return tags
    return tags


def merge_hashtags(emotion_tags: list[str], keyword_tags: list[str]) -> list[str]:
    """MID-08: emotion 정적 + 키워드 해시태그 dedupe 합산.

    키워드 해시태그를 앞에 두어 더 구체적인 정보가 먼저 노출되게 한다.
    YouTube 권장 해시태그 15개 한도를 넘지 않는다.
    """
    merged: list[str] = []
    seen: set[str] = set()
    for tag in keyword_tags + emotion_tags:
        if tag in seen:
            continue
        seen.add(tag)
        merged.append(tag)
        if len(merged) >= _HASHTAG_TOTAL_MAX_COUNT:
            break
    return merged


def _sanitize_clickbait(text: str) -> tuple[str, bool]:
    """Replace clickbait words with neutral alternates.

    Returns (sanitized_text, was_modified). Longer phrases are matched first
    so that "충격적" is replaced before "충격" and never leaves residue.
    """
    modified = False
    out = text
    for word in sorted(BANNED_CLICKBAIT_WORDS, key=len, reverse=True):
        if word in out:
            out = out.replace(word, BANNED_CLICKBAIT_WORDS[word])
            modified = True
    return out, modified


def _strip_clickbait(text: str) -> str:
    """Remove banned words entirely (used to extract a fact kernel for fallback titles)."""
    out = text
    for word in sorted(BANNED_CLICKBAIT_WORDS, key=len, reverse=True):
        out = out.replace(word, "")
    return " ".join(out.split()).strip("!?.,~ ")


def _build_fact_based_title(script: ShortsScript) -> str:
    """Fact-based fallback title used when the original contains banned clickbait words.

    Why: YouTube spam/clickbait policies penalize sensational titles. Falling back to
    "[국회] 발언자/주제 — N초 정리" 형태로 재생성해 채널 신뢰도를 지킨다.
    """
    prefix = "[국회]" if script.metadata.source_type == "political" else "[정리]"
    duration = int(script.metadata.duration)

    fact_kernel = _strip_clickbait(script.metadata.title)
    if not fact_kernel and script.scenes:
        first_text = script.scenes[0].text.replace("\n", " ").strip()
        fact_kernel = _strip_clickbait(first_text)
    if not fact_kernel:
        fact_kernel = "주요 발언"

    suffix = f" — {duration}초 정리"
    budget = 100 - len(prefix) - 1 - len(suffix)
    if len(fact_kernel) > budget:
        fact_kernel = fact_kernel[:budget].rstrip()
    return f"{prefix} {fact_kernel}{suffix}"


def generate_metadata(script: ShortsScript) -> dict:
    """Generate YouTube upload metadata from a ShortsScript.

    Returns dict with title, description, tags.
    """
    emotion = script.metadata.emotion_type
    raw_title = script.metadata.title

    # QW-08: 금칙어 매치 시 사실 기반 fallback 제목으로 재생성한다.
    _, title_had_clickbait = _sanitize_clickbait(raw_title)
    if title_had_clickbait:
        title = _build_fact_based_title(script)
    else:
        title = raw_title

    emotion_hashtags = EMOTION_HASHTAGS.get(emotion, EMOTION_HASHTAGS["relatable"])
    # MID-08: highlight_words 기반 해시태그를 emotion 정적과 결합
    keyword_hashtags = extract_keyword_hashtags(script)
    hashtags = merge_hashtags(emotion_hashtags, keyword_hashtags)

    description_lines = [
        title,
        "",
        "블라인드 인기글을 만화 쇼츠로 만들었습니다.",
        "",
        f"감정: {emotion}",
        f"길이: {script.metadata.duration}초",
        "",
        "⚠️ 본 영상은 커뮤니티 게시글을 AI로 재구성한 콘텐츠입니다.",
        "개인정보는 모두 마스킹 처리되었습니다.",
        "",
        " ".join(hashtags),
        "",
        "👍 좋아요와 구독은 큰 힘이 됩니다!",
    ]

    tags = [
        "블라인드", "직장인", "쇼츠", "shorts",
        script.metadata.emotion_type,
        "만화", "웹툰", "AI",
    ]

    # Extract keywords from scenes for tags
    for scene in script.scenes[:3]:
        words = scene.text.replace("\n", " ").split()
        for w in words:
            clean = w.strip(".,!?~\"'")
            if len(clean) >= 2 and clean not in tags:
                tags.append(clean)
            if len(tags) >= 20:
                break

    # 3-line summary: fixed intro + 2 sentences summarizing full content
    body_texts = " ".join(
        s.text.replace("\n", " ").strip()
        for s in script.scenes
        if s.type in ("body", "comment")
    )
    # Take first ~2 meaningful chunks as summary sentences
    sentences = [seg.strip() for seg in body_texts.replace(".", ".||").replace("?", "?||").replace("!", "!||").split("||") if seg.strip()]
    line2 = sentences[0] if sentences else ""
    line3 = sentences[1] if len(sentences) > 1 else (sentences[0] if sentences else "")
    summary = (
        "다양한 커뮤니티의 핫한 게시글을 영상으로 보여드립니다\n"
        f"{line2.rstrip('.')}\n"
        f"{line3.rstrip('.')}"
    )

    hashtags_str = " ".join(hashtags)

    description_text = "\n".join(description_lines)
    sanitized_description, _ = _sanitize_clickbait(description_text)
    sanitized_summary, _ = _sanitize_clickbait(summary)
    sanitized_tags = []
    for t in tags:
        cleaned, _ = _sanitize_clickbait(t)
        if cleaned and cleaned not in sanitized_tags:
            sanitized_tags.append(cleaned)

    return {
        "title": title[:100],
        "description": sanitized_description,
        "tags": sanitized_tags[:30],
        "summary": sanitized_summary,
        "hashtags": hashtags_str,
    }
