"""Subtitle translation via OpenAI GPT-4o-mini.

Translates Korean scene texts to English or Japanese.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Raised when translation fails."""


def translate_subtitles(
    scenes: list[dict],
    target_language: str = "en",
) -> list[dict]:
    """Translate scene texts to target language.

    Args:
        scenes: List of {id, text} dicts
        target_language: "en" or "ja"

    Returns:
        List of {scene_id, translated_text} dicts
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise TranslationError("OPENAI_API_KEY가 설정되지 않았습니다")

    lang_name = {"en": "English", "ja": "Japanese"}.get(target_language)
    if not lang_name:
        raise TranslationError(f"지원하지 않는 언어: {target_language}")

    texts = [{"id": s["id"], "text": s["text"]} for s in scenes]

    prompt = f"""Translate the following Korean subtitle texts to {lang_name}.
Keep the translations concise and natural for video subtitles.
Maintain line breaks where they exist.

Input:
{json.dumps(texts, ensure_ascii=False)}

Output as JSON array: [{{"id": number, "translated_text": string}}]
Only output the JSON array, nothing else."""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content or "[]"
        # Extract JSON from response
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        translations = json.loads(content)
        return [
            {
                "scene_id": t["id"],
                "translated_text": t["translated_text"],
            }
            for t in translations
        ]

    except ImportError:
        raise TranslationError("openai 패키지가 설치되지 않았습니다: pip install openai")
    except json.JSONDecodeError as e:
        raise TranslationError(f"번역 결과 파싱 실패: {e}")
    except Exception as e:
        raise TranslationError(f"번역 실패: {e}")
