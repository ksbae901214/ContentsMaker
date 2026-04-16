"""Auto clip selection from transcript.

Selects the highest-impact segment from a VTT transcript
using keyword density scoring and a sliding window approach.
"""
from __future__ import annotations

# Keywords indicating impactful political speech moments, weighted by tier.
_HIGH_KEYWORDS = [
    "충격", "논란", "폭로", "거짓", "위기", "망언", "경악", "반박",
    "사실", "충돌", "반격", "탄핵", "고발", "비위", "의혹",
]
_MEDIUM_KEYWORDS = [
    "반대", "찬성", "요구", "주장", "강조", "지적", "문제", "비판",
    "지지", "발언", "경고", "주목", "중요", "핵심", "우려",
]
_LOW_KEYWORDS = [
    "설명", "언급", "질의", "답변", "토론", "회의", "검토", "논의",
]


def _score_text(text: str) -> float:
    s = 0.0
    for kw in _HIGH_KEYWORDS:
        s += text.count(kw) * 3.0
    for kw in _MEDIUM_KEYWORDS:
        s += text.count(kw) * 1.5
    for kw in _LOW_KEYWORDS:
        s += text.count(kw) * 0.5
    return s


def select_best_clip(
    transcript: list[dict],
    max_duration: float = 55.0,
) -> tuple[float, float]:
    """Select the highest-impact segment from a transcript.

    Uses a sliding window of `max_duration` seconds and scores each
    window by the density of high-impact political keywords.

    Args:
        transcript: List of {"start": float, "end": float, "text": str}
                    from parse_vtt_subtitles().
        max_duration: Maximum clip duration in seconds. Defaults to 55s
                      to leave headroom within the 60s Shorts limit.

    Returns:
        (start_time, end_time) in seconds. Falls back to (0, min(total, max_duration))
        when transcript is empty or shorter than max_duration.
    """
    if not transcript:
        return 0.0, max_duration

    total_start = transcript[0]["start"]
    total_end = transcript[-1]["end"]
    total_duration = total_end - total_start

    if total_duration <= max_duration:
        return total_start, total_end

    best_start = total_start
    best_score = -1.0

    for seg in transcript:
        window_start = seg["start"]
        window_end = window_start + max_duration

        window_text = " ".join(
            s["text"]
            for s in transcript
            if s["start"] >= window_start and s["end"] <= window_end
        )
        score = _score_text(window_text)

        if score > best_score:
            best_score = score
            best_start = window_start

    best_end = min(best_start + max_duration, total_end)
    return best_start, best_end
