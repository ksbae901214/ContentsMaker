"""3가지 TTS 보이스 샘플 생성 — A/B/C 옵션 비교용."""
import asyncio
from pathlib import Path

import edge_tts

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "tts_samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_TEXT = (
    "안녕하세요! 오늘은 요즘 가장 핫한 이야기를 들고 왔어요. "
    "끝까지 보시면 진짜 반전이 기다리고 있답니다. "
    "좋아요와 구독은 큰 힘이 됩니다!"
)

OPTIONS = [
    # edge-tts 무료 티어 한국어 여성 = SunHiNeural 하나뿐. pitch/rate로 톤 조정.
    ("A_SunHi_base",    "ko-KR-SunHiNeural", "+20%", "+0Hz",  "현재 기본값 (비교 기준)"),
    ("B_SunHi_young",   "ko-KR-SunHiNeural", "+15%", "+10Hz", "피치 ↑ — 밝고 젊은 톤"),
    ("C_SunHi_soft",    "ko-KR-SunHiNeural", "+10%", "+5Hz",  "피치 ↑ + 속도 ↓ — 부드럽게"),
]


async def synth(label: str, voice: str, rate: str, pitch: str, desc: str) -> Path:
    out = OUT_DIR / f"{label}.mp3"
    communicate = edge_tts.Communicate(SAMPLE_TEXT, voice, rate=rate, pitch=pitch)
    await communicate.save(str(out))
    print(f"✓ {label:20} | {voice:22} | rate={rate:5} pitch={pitch:5} | {desc}")
    print(f"  → {out}")
    return out


async def main() -> None:
    print(f"샘플 텍스트: {SAMPLE_TEXT}\n")
    print(f"출력 디렉토리: {OUT_DIR}\n")
    # Sequential to avoid Azure rate limits triggering "NoAudioReceived"
    for opt in OPTIONS:
        await synth(*opt)
    print(f"\n완료! 아래 파일을 열어 비교하세요:")
    for label, *_ in OPTIONS:
        print(f"  open {OUT_DIR / f'{label}.mp3'}")


if __name__ == "__main__":
    asyncio.run(main())
