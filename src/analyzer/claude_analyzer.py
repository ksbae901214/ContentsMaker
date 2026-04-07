"""Claude Code analyzer — converts BlindPost to ShortsScript.

Calls Claude Code CLI via subprocess to analyze content and generate
a structured ShortsScript JSON.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from src.analyzer.prompt_template import build_prompt, build_topic_prompt
from src.analyzer.script_models import ShortsScript, Metadata, AudioConfig, BackgroundConfig
from src.config.settings import DATA_SCRIPTS_DIR, CLAUDE_TIMEOUT_SECONDS
from src.scraper.models import BlindPost
from src.tts.voice_config import get_voice_config, get_gradient

logger = logging.getLogger(__name__)


class AnalyzerError(Exception):
    """Raised when analysis fails."""


def analyze(post: BlindPost, output_dir: Path | None = None) -> tuple[ShortsScript, Path]:
    """Analyze a BlindPost and generate a ShortsScript.

    Returns (ShortsScript, file_path) tuple.
    """
    prompt = build_prompt(
        title=post.title,
        author=post.author,
        body=post.body,
        comments=[c.to_dict() for c in post.comments],
    )

    logger.info("Claude Code 분석 시작: %s", post.title)
    raw_json = _call_claude(prompt)
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

    return script, file_path


def analyze_topic(
    topic_input,
    output_dir: Path | None = None,
) -> tuple[ShortsScript, Path]:
    """Analyze a TopicInput and generate a ShortsScript.

    Returns (ShortsScript, file_path) tuple.
    """
    prompt = build_topic_prompt(
        topic=topic_input.topic,
        style=topic_input.style,
        tone=topic_input.tone,
        details=topic_input.details,
    )

    logger.info("Claude Code 주제 분석 시작: %s", topic_input.topic)
    raw_json = _call_claude(prompt)
    script = _parse_response(raw_json)

    # Ensure source_type is "topic"
    if script.metadata.source_type != "topic":
        script = ShortsScript(
            metadata=Metadata(
                title=script.metadata.title,
                emotion_type=script.metadata.emotion_type,
                duration=script.metadata.duration,
                source_url=script.metadata.source_url,
                source_type="topic",
            ),
            scenes=script.scenes,
            audio=script.audio,
            background=script.background,
        )

    script = _apply_voice_config(script)
    script = _ensure_line_breaks(script)

    target_dir = output_dir or DATA_SCRIPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = "".join(
        c for c in topic_input.topic[:30] if c.isalnum() or c in " _-"
    )
    safe_topic = safe_topic.strip().replace(" ", "_") or "topic"
    filename = f"{timestamp}_{safe_topic}.json"
    file_path = target_dir / filename

    script.save(file_path)
    logger.info("주제 스크립트 저장: %s", file_path)

    return script, file_path


def _call_claude(prompt: str) -> str:
    """Call Claude Code headless mode and return raw output."""
    try:
        env = {
            **os.environ,
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:" + os.environ.get("PATH", ""),
        }
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
            env=env,
        )
    except FileNotFoundError:
        raise AnalyzerError(
            "Claude Code가 설치되지 않았습니다. "
            "'claude' 명령어가 PATH에 있는지 확인하세요."
        )
    except subprocess.TimeoutExpired:
        raise AnalyzerError(
            f"Claude Code 응답 시간 초과 ({CLAUDE_TIMEOUT_SECONDS}초). "
            "네트워크 상태를 확인하세요."
        )

    if result.returncode != 0:
        stderr = result.stderr[:300] if result.stderr else ""
        raise AnalyzerError(f"Claude Code 실행 실패 (exit {result.returncode}): {stderr}")

    output = result.stdout.strip()
    if not output:
        raise AnalyzerError("Claude Code가 빈 응답을 반환했습니다.")

    return output


def _parse_response(raw: str) -> ShortsScript:
    """Parse Claude Code's response into a ShortsScript."""
    # Try direct JSON parse first
    try:
        data = json.loads(raw)
        # Handle Claude Code --output-format json wrapper
        if isinstance(data, dict) and "result" in data:
            inner = data["result"]
            if isinstance(inner, str):
                return _parse_response(inner)
            if isinstance(inner, dict):
                data = inner
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
        f"Claude Code 응답을 JSON으로 파싱할 수 없습니다.\n응답 미리보기: {raw[:300]}"
    )


def _ensure_line_breaks(script: ShortsScript) -> ShortsScript:
    """Fallback: add line breaks if AI didn't insert them (15 chars max per line)."""
    from src.analyzer.script_models import Scene

    new_scenes = []
    for scene in script.scenes:
        text = scene.text
        if "\n" not in text and len(text) > 15:
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
