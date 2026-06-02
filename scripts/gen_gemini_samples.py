"""Gemini TTS 3개 보이스 샘플 생성 — Leda / Aoede / Kore 비교용.

사용법:
    export GEMINI_API_KEY="your_key_here"
    python3 scripts/gen_gemini_samples.py
"""
from __future__ import annotations

import os
import struct
import sys
import wave
from pathlib import Path

from google import genai
from google.genai import types

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "tts_samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_TEXT = (
    "안녕하세요! 오늘은 요즘 가장 핫한 이야기를 들고 왔어요. "
    "끝까지 보시면 진짜 반전이 기다리고 있답니다. "
    "좋아요와 구독은 큰 힘이 됩니다!"
)

VOICES = [
    ("Leda",   "젊고 에너지 있는 (youthful, energetic)"),
    ("Aoede",  "경쾌하고 자연스러운 (breezy, natural)"),
    ("Kore",   "단단하고 자신감 있는 (firm, confident)"),
]

MODEL = "gemini-2.5-flash-preview-tts"
SAMPLE_RATE = 24000  # Gemini TTS는 24kHz 16bit mono PCM 반환


def pcm_to_wav(pcm_bytes: bytes, out_path: Path) -> None:
    """Gemini가 반환한 생 PCM을 WAV 파일로 저장."""
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)          # mono
        wf.setsampwidth(2)          # 16bit = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)


def synth(client: genai.Client, voice: str, desc: str) -> Path:
    out_path = OUT_DIR / f"gemini_{voice}.wav"
    print(f"⏳ {voice:8} | {desc}")

    response = client.models.generate_content(
        model=MODEL,
        contents=SAMPLE_TEXT,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    ),
                ),
            ),
        ),
    )

    pcm = response.candidates[0].content.parts[0].inline_data.data
    pcm_to_wav(pcm, out_path)
    size_kb = out_path.stat().st_size // 1024
    print(f"✓ {voice:8} | {size_kb} KB | {out_path}")
    return out_path


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        print("   https://aistudio.google.com/app/apikey 에서 발급 후:", file=sys.stderr)
        print("   export GEMINI_API_KEY='your_key'", file=sys.stderr)
        return 1

    client = genai.Client(api_key=api_key)
    print(f"샘플 텍스트: {SAMPLE_TEXT}")
    print(f"출력 디렉토리: {OUT_DIR}")
    print(f"모델: {MODEL}\n")

    for voice, desc in VOICES:
        try:
            synth(client, voice, desc)
        except Exception as e:
            print(f"✗ {voice:8} | 실패: {e}", file=sys.stderr)

    print(f"\n완료! Finder 열기:\n  open {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
