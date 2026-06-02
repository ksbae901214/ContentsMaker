# Implementation Plan: Analyzer + TTS Module

**Branch**: `002-analyzer-tts` | **Date**: 2026-03-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-analyzer-tts/spec.md`

## Summary

raw_content.json(블라인드 글)을 Claude Code(Sonnet 4.6)로 분석하여 ShortsScript JSON을 생성하고, edge-tts로 감정별 한국어 음성을 생성하는 파이프라인 2-3단계 구현.

## Technical Context

**Language/Version**: Python 3.11+ (3.10 호환)
**Primary Dependencies**: edge-tts (무료 TTS), subprocess (Claude Code 호출)
**Storage**: JSON 파일 (`data/scripts/`), MP3 파일 (`data/audio/`)
**Testing**: pytest, pytest-asyncio (edge-tts는 async)
**Target Platform**: macOS (로컬), Linux 호환
**Project Type**: CLI 파이프라인 모듈
**Performance Goals**: raw → script 2분 이내, script → voice 30초 이내
**Constraints**: Claude Code 로컬 설치 필수, edge-tts 인터넷 연결 필수

## Constitution Check

| 원칙 | 상태 | 근거 |
|------|------|------|
| I. Zero-Cost | ✅ Pass | Claude Code 직접 사용 (API 비용 $0), edge-tts 완전 무료 |
| II. Pipeline Integrity | ✅ Pass | raw_content.json → script.json → voice.mp3, 각 단계 독립 실행 |
| III. Text-First | ✅ N/A | 영상 모듈에서 적용 |
| IV. Content Safety | ✅ Pass | Analyzer 프롬프트에 개인정보 마스킹 지시 포함 |
| V. Emotion-Driven | ✅ Pass | 4종 감정 자동 분류 + 감정별 음성 설정 |
| VI. Modularity | ✅ Pass | analyzer, tts 별도 모듈, 독립 실행 가능 |
| VII. Evidence-Based | ✅ Pass | 4종 감정 샘플로 검증 예정 |

## Project Structure

### Source Code

```text
src/
├── analyzer/
│   ├── __init__.py
│   ├── claude_analyzer.py    # Claude Code 호출 + JSON 파싱
│   ├── prompt_template.py    # 프롬프트 템플릿
│   └── script_models.py      # ShortsScript, Scene 데이터 클래스
├── tts/
│   ├── __init__.py
│   ├── edge_tts_generator.py # edge-tts 래퍼
│   └── voice_config.py       # 감정별 음성 설정
├── config/
│   └── settings.py            # + DATA_SCRIPTS_DIR, DATA_AUDIO_DIR 추가
└── main.py                    # + analyze, tts 서브커맨드 추가

data/
├── raw/        # (기존) 크롤링/수동 입력 JSON
├── scripts/    # (신규) script.json
└── audio/      # (신규) voice.mp3
```

## Data Model

### ShortsScript (script.json)

```python
@dataclass(frozen=True)
class Scene:
    id: int
    timestamp: float       # 시작 시각 (초)
    duration: float        # 지속 시간 (초)
    type: str              # "title" | "body" | "comment"
    text: str              # 화면 표시 텍스트
    voice_text: str        # TTS용 텍스트
    emphasis: str           # "high" | "medium" | "low"

@dataclass(frozen=True)
class ShortsScript:
    metadata: Metadata      # {title, emotion_type, duration, source_url}
    scenes: tuple[Scene, ...]
    audio: AudioConfig      # {tts_script, voice, rate, pitch}
    background: BackgroundConfig  # {type, colors}
```

### 감정별 음성 설정 (voice_config.py)

```python
VOICE_CONFIG = {
    "funny":     {"voice": "ko-KR-BongJinNeural",   "rate": "+15%", "pitch": "+5Hz"},
    "touching":  {"voice": "ko-KR-SunHiNeural",     "rate": "-10%", "pitch": "-3Hz"},
    "angry":     {"voice": "ko-KR-InJoonNeural",    "rate": "+5%",  "pitch": "-10Hz"},
    "relatable": {"voice": "ko-KR-SeoHyeonNeural",  "rate": "+0%",  "pitch": "+0Hz"},
}
```

### Claude Code 호출 방식

```bash
claude -p "$(cat prompt.txt)" --output-format json
```

Python subprocess로 호출, stdout에서 JSON 파싱.

## CLI Interface

```bash
# Analyzer만 실행
python3 -m src.main analyze --file data/raw/post.json

# TTS만 실행
python3 -m src.main tts --file data/scripts/script.json

# 통합 (analyze → tts)
python3 -m src.main analyze --file data/raw/post.json --with-tts
```
