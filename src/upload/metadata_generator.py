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


def generate_metadata(script: ShortsScript) -> dict:
    """Generate YouTube upload metadata from a ShortsScript.

    Returns dict with title, description, tags.
    """
    emotion = script.metadata.emotion_type
    title = f"[블라인드] {script.metadata.title}"

    hashtags = EMOTION_HASHTAGS.get(emotion, EMOTION_HASHTAGS["relatable"])

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

    return {
        "title": title[:100],
        "description": "\n".join(description_lines),
        "tags": tags[:30],
        "summary": summary,
        "hashtags": hashtags_str,
    }
