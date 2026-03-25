"""AI analyzer — converts BlindPost to ShortsScript.

Uses OpenAI GPT-4o-mini to analyze content and generate
a structured ShortsScript JSON.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from src.analyzer.prompt_template import build_prompt
from src.analyzer.script_models import ShortsScript, AudioConfig, BackgroundConfig
from src.config.settings import DATA_SCRIPTS_DIR
from src.scraper.models import BlindPost
from src.tts.voice_config import get_voice_config, get_gradient

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Raised when analysis fails."""


def analyze(post: BlindPost, output_dir: Path | None = None) -> ShortsScript:
    """Analyze a BlindPost and generate a ShortsScript.

    1. Build prompt from post data
    2. Call Claude Code via subprocess
    3. Parse JSON response
    4. Fill in voice config and gradient based on emotion
    5. Save and return ShortsScript
    """
    prompt = build_prompt(
        title=post.title,
        author=post.author,
        body=post.body,
        comments=[c.to_dict() for c in post.comments],
    )

    logger.info("AI 분석 시작: %s", post.title)
    raw_json = _call_openai(prompt)
    script = _parse_response(raw_json)
    script = _apply_voice_config(script)
    script = _ensure_line_breaks(script)

    target_dir = output_dir or DATA_SCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in post.title[:30] if c.isalnum() or c in " _-")
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    filename = f"{timestamp}_{safe_title}.json"
    file_path = target_dir / filename

    script.save(file_path)
    logger.info("스크립트 저장: %s", file_path)

    return script


def _call_openai(prompt: str) -> str:
    """Call OpenAI GPT-4o-mini to analyze content."""
    try:
        from openai import OpenAI
    except ImportError:
        raise AnalyzerError("openai 패키지가 필요합니다: pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AnalyzerError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 블라인드 커뮤니티 게시글을 유튜브 쇼츠 영상 스크립트로 변환하는 전문가입니다. JSON만 출력하세요."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4000,
            temperature=0.3,
        )
        result = response.choices[0].message.content or ""
        logger.info("GPT-4o-mini 분석 완료 (%d자)", len(result))
        return result
    except Exception as e:
        raise AnalyzerError(f"OpenAI API 호출 실패: {e}")


def _parse_response(raw: str) -> ShortsScript:
    """Parse API response into a ShortsScript."""
    if not raw or not raw.strip():
        raise AnalyzerError("AI 응답이 비어있습니다.")

    # Try direct JSON parse first
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "metadata" in data:
            return ShortsScript.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        pass

    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            return ShortsScript.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # Try to find raw JSON object in text
    brace_match = re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        try:
            data = json.loads(brace_match.group(0))
            return ShortsScript.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    raise AnalyzerError(
        f"AI 응답을 JSON으로 파싱할 수 없습니다.\n응답 미리보기: {raw[:300]}"
    )


def _ensure_line_breaks(script: ShortsScript) -> ShortsScript:
    """Fallback: add line breaks if AI didn't insert them (15 chars max per line)."""
    from src.analyzer.script_models import Scene

    new_scenes = []
    for scene in script.scenes:
        text = scene.text
        if "\n" not in text and len(text) > 15:
            # Simple fallback: break at particles/spaces near 15-char boundary
            words = text.replace(" ", " ").split(" ")
            lines = []
            current = ""
            for word in words:
                if current and len(current) + len(word) + 1 > 15:
                    lines.append(current)
                    current = word
                else:
                    current = f"{current} {word}" if current else word
            if current:
                lines.append(current)
            text = "\n".join(lines)

        new_scenes.append(Scene(
            id=scene.id,
            timestamp=scene.timestamp,
            duration=scene.duration,
            type=scene.type,
            text=text,
            voice_text=scene.voice_text,
            emphasis=scene.emphasis,
            highlight_words=scene.highlight_words,
        ))

    return ShortsScript(
        metadata=script.metadata,
        scenes=tuple(new_scenes),
        audio=script.audio,
        background=script.background,
    )


def _apply_voice_config(script: ShortsScript) -> ShortsScript:
    """Fill in voice config and gradient based on emotion type."""
    emotion = script.metadata.emotion_type
    vc = get_voice_config(emotion)
    gradient = get_gradient(emotion)

    new_audio = AudioConfig(
        tts_script=script.audio.tts_script,
        voice=vc["voice"],
        rate=vc["rate"],
        pitch=vc["pitch"],
    )
    new_bg = BackgroundConfig(
        type="gradient",
        colors=tuple(gradient),
    )

    return ShortsScript(
        metadata=script.metadata,
        scenes=script.scenes,
        audio=new_audio,
        background=new_bg,
    )
