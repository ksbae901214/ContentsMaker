"""자막 큐 생성 (Feature 027 Phase 2).

YouTube VTT 자막을 클립 기준 상대 시간으로 변환한다.
VTT 없으면 download_subtitles → transcribe_video_or_fallback 순서로 폴백.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from src.jpolitics.logger import logger
from src.jpolitics.models.clip import CaptionCue
from src.jpolitics.models.moment import Moment

# 1줄 권장 글자 수 (이 이상이면 2줄로 분리)
_LINE_SPLIT_CHARS = 20


def _split_to_lines(text: str) -> str:
    """긴 텍스트를 1~2줄로 분리 (공백 기준, ~20자)."""
    text = text.strip()
    if len(text) <= _LINE_SPLIT_CHARS:
        return text

    words = text.split(" ")
    if len(words) == 1:
        # 공백 없는 긴 텍스트: 중간에서 분리
        mid = len(text) // 2
        return text[:mid] + "\n" + text[mid:]

    # 누적 길이 기준으로 첫 줄/둘째 줄 분리
    line1: list[str] = []
    line2: list[str] = []
    acc = 0
    split_done = False
    for word in words:
        if not split_done and acc + len(word) > _LINE_SPLIT_CHARS:
            split_done = True
        if not split_done:
            line1.append(word)
            acc += len(word) + 1
        else:
            line2.append(word)

    if not line1:
        line1 = [words[0]]
        line2 = words[1:]

    result = " ".join(line1)
    if line2:
        result += "\n" + " ".join(line2)
    return result


def _deduplicate_consecutive(cues: list[CaptionCue]) -> list[CaptionCue]:
    """연속으로 동일한 text 큐 제거 (YouTube 자동자막 누적 방식 처리)."""
    out: list[CaptionCue] = []
    prev_text = ""
    for cue in cues:
        if cue.text == prev_text:
            continue
        out.append(cue)
        prev_text = cue.text
    return out


def _parse_vtt_to_raw_cues(vtt_path: Path) -> list[dict]:
    """VTT 파일을 [{start, end, text}] 로 파싱 (src.scraper 미사용, 내부 구현)."""
    VTT_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")

    def _ts(s: str) -> float:
        m = VTT_TS.match(s.strip())
        if not m:
            return 0.0
        h, mn, sec, ms = int(m[1]), int(m[2]), int(m[3]), int(m[4])
        return h * 3600 + mn * 60 + sec + ms / 1000

    lines = vtt_path.read_text(encoding="utf-8").splitlines()
    raw: list[dict] = []
    prev_text = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            parts = line.split("-->")
            start = _ts(parts[0])
            end = _ts(parts[1].split()[0])
            text_parts: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip():
                cleaned = re.sub(r"<[^>]+>", "", lines[i]).strip()
                if cleaned:
                    text_parts.append(cleaned)
                i += 1
            text = " ".join(text_parts)
            if text and text != prev_text:
                raw.append({"start": start, "end": end, "text": text})
                prev_text = text
        else:
            i += 1
    return raw


def _segments_to_cues(
    segments: list[dict],
    clip_start: float,
    clip_end: float,
) -> list[CaptionCue]:
    """segments [{"start", "end", "text"}] → 클립 기준 CaptionCue 목록.

    - clip_start~clip_end 와 겹치는 큐만 포함
    - 상대 시간으로 변환 (clip_start 기준)
    - 음수 start_sec → 0으로 클램프
    - 텍스트 1~2줄 분리
    """
    cues: list[CaptionCue] = []
    for seg in segments:
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", 0.0))
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        # 겹침 조건: seg_end > clip_start AND seg_start < clip_end
        if seg_end <= clip_start or seg_start >= clip_end:
            continue
        rel_start = max(0.0, seg_start - clip_start)
        rel_end = max(0.0, seg_end - clip_start)
        cues.append(CaptionCue(
            start_sec=rel_start,
            end_sec=rel_end,
            text=_split_to_lines(text),
        ))
    return _deduplicate_consecutive(cues)


def build_caption_cues(
    work_dir: Path,
    source_url: str,
    video_path: Path,
    moment: Moment,
    pad_before: float,
) -> list[CaptionCue]:
    """모먼트에 해당하는 자막 큐 목록을 반환한다.

    1. work_dir 내 기존 *.vtt 파일 재사용
    2. 없으면 download_subtitles() 시도
    3. 실패하면 transcribe_video_or_fallback() 폴백

    Args:
        work_dir: 작업 디렉터리 (VTT 파일 탐색 + 저장 위치).
        source_url: YouTube URL (자막 다운로드용).
        video_path: 원본 영상 경로 (Whisper 폴백용).
        moment: 자막을 필터링할 모먼트.
        pad_before: 클립 시작 여유 (초).

    Returns:
        클립 기준 상대 시간 CaptionCue 목록.
    """
    clip_start = max(0.0, moment.start_sec - pad_before)
    clip_end = moment.end_sec + pad_before  # 종료 여유도 pad_before 기준

    # 1. 기존 VTT 파일 탐색
    existing_vtt = sorted(work_dir.glob("*.vtt"))
    if existing_vtt:
        vtt_path = existing_vtt[-1]
        logger.info("기존 VTT 파일 재사용: %s", vtt_path.name)
        raw = _parse_vtt_to_raw_cues(vtt_path)
        return _segments_to_cues(raw, clip_start, clip_end)

    # 2. download_subtitles() 시도
    try:
        from src.scraper.youtube_downloader import download_subtitles  # read-only import
        vtt_path = download_subtitles(source_url, work_dir)
        if vtt_path is not None:
            logger.info("자막 다운로드 완료: %s", vtt_path.name)
            raw = _parse_vtt_to_raw_cues(vtt_path)
            return _segments_to_cues(raw, clip_start, clip_end)
        logger.warning("자막 없음 — transcript 폴백 시도")
    except Exception as exc:
        logger.warning("download_subtitles 실패: %s — transcript 폴백", exc)

    # 3. transcribe_video_or_fallback() 폴백
    from src.scraper.youtube_downloader import transcribe_video_or_fallback  # read-only import
    segments = transcribe_video_or_fallback(
        url=source_url,
        video_path=video_path,
        out_dir=work_dir,
    )
    return _segments_to_cues(segments, clip_start, clip_end)


def save_caption_cues(cues: list[CaptionCue], work_dir: Path, n: int) -> Path:
    """work_dir/captions_{n}.json 으로 저장."""
    work_dir.mkdir(parents=True, exist_ok=True)
    out = work_dir / f"captions_{n}.json"
    out.write_text(
        json.dumps([c.to_dict() for c in cues], ensure_ascii=False, indent=2)
    )
    return out
