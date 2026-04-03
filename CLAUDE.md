# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

ContentsMaker converts Blind community posts and free-topic inputs into manga-style or AI-video YouTube Shorts (9:16 vertical, 30-60 seconds). The pipeline: text extraction → AI analysis → image/video generation → TTS → video rendering. Cost: ~$0.03/video (image mode), ~$0.25/video (video mode).

## Commands

```bash
# Development
npm run dev                              # Next.js dev server (localhost:3000)
npm run build                            # Production build

# Python tests
python3 -m pytest tests/ -v             # All tests
python3 -m pytest tests/test_analyzer.py -v   # Single file
python3 -m pytest tests/test_models.py::test_scene_from_dict -v  # Single test

# Lint
ruff check .                             # Python lint

# CLI pipeline
python3 -m src.main image screenshot.png        # Screenshot → video
python3 -m src.main manual --file data/raw/x.json  # JSON → video
python3 -m src.main pipeline --file data/raw/x.json  # Full pipeline

# Install
pip install -r requirements.txt          # Python deps
npm install                              # Node deps (root)
cd src/video/remotion && npm install     # Remotion deps (separate package.json)
```

## Architecture

### Pipeline Flow

```
Input (screenshot/URL/text/topic) → BlindPost or TopicInput JSON (data/raw/)
  → Claude analyzer → ShortsScript JSON (data/scripts/)
    → GPT Image API → manga PNGs (data/images/)       [manga mode]
    → Seedance API → video clips MP4 (data/videos/)    [video mode]
    → edge-tts → voice MP3 + timing JSON (data/audio/)
      → Remotion render → MP4 (data/outputs/)
```

### Two Entry Points

1. **Web UI** (`app/`): Next.js 16 app. Main generation endpoint is `POST /api/generate` which streams progress via SSE.
2. **CLI** (`src/main.py`): Python CLI with subcommands (`image`, `manual`, `analyze`, `tts`, `render`, `pipeline`).

### Python Backend (`src/`)

| Module | Purpose | Key Detail |
|--------|---------|------------|
| `scraper/` | Content ingestion | `image_extractor.py` (OCR), `topic_input.py` (free-topic input) |
| `analyzer/` | AI script generation | `claude_analyzer.py` (`analyze()` + `analyze_topic()`); `prompt_template.py` (Blind + Topic prompts) |
| `illustrator/` | Manga image generation | GPT Image API (`gpt-image-1`), 4 image styles (webtoon/3d_pixar/realistic/anime) |
| `tts/` | Voice synthesis | `edge-tts` (free, async); `voice_config.py` maps emotion → voice/colors/gradient |
| `video/` | Video rendering | `renderer.py` wraps Remotion CLI; copies images/videos/audio to `public/` |
| `video_gen/` | AI video generation | `seedance_gen.py` (Seedance API), `base.py` (abstract + `generate_and_wait()`) |
| `editor/` | Scene editing | `scene_ops.py` (split/merge/reorder/resize), `batch.py`, `project.py`, `translator.py` |
| `config/settings.py` | Global paths & constants | `PROJECT_ROOT`, `DATA_*_DIR`, `CLAUDE_TIMEOUT_SECONDS=300` |

### Remotion Video (`src/video/remotion/`)

Separate npm package. React components render the video:
- `Root.tsx` — composition registry ("BlindShorts")
- `ShortsComposition.tsx` — main layout: background + scenes + audio + transitions + outro
- `components/` — `Background.tsx`, `SceneText.tsx`, `Transition.tsx`, `SceneWithVideo.tsx`

Renderer converts Python snake_case to JS camelCase via `_convert_to_camel_case()` before passing props.

### Frontend (`app/`)

- `page.tsx` — main UI with 4 input tabs (image/manual/URL/topic), visual mode toggle, image style selector
- `components/` — `SceneEditor.tsx` (timeline), `PreviewComposition.tsx` (Remotion player), etc.
- `api/generate/route.ts` — SSE streaming endpoint; orchestrates the full pipeline via Python subprocess calls
- `api/scene/` — scene editing endpoints (split, merge, style, transition, image regeneration)
- `api/project/` — save/load/delete project state

### Central Data Model

`ShortsScript` (`src/analyzer/script_models.py`) is the pipeline's core data structure — all frozen dataclasses:
- `Metadata` (title, emotion_type: funny|touching|angry|relatable, duration, source_type: blind|topic)
- `Scene` (id, timestamp, duration, type: title|body|comment, text, voice_text, emphasis, highlight_words, subtitle_style, transition, sfx)
- `AudioConfig` (tts_script, voice, rate, pitch)
- `BackgroundConfig` (type, colors)

Uses manual `to_dict()`/`from_dict()` for serialization (not `dataclasses.asdict()`). Handles both snake_case and camelCase keys on deserialization.

### Emotion System

`voice_config.py` defines per-emotion settings used across the pipeline:
- `GRADIENT_THEMES` — background colors per emotion
- `HIGHLIGHT_COLORS` — keyword highlight color per emotion
- `VOICE_CONFIG` — TTS voice/rate/pitch per emotion
- All emotions currently use `ko-KR-SunHiNeural` at `+20%` rate

## Key Conventions

- **All Python data models are frozen dataclasses** (immutable). Create new instances instead of mutating.
- **Python modules import from `src.*`** (e.g., `from src.config.settings import PROJECT_ROOT`). The project root is on `PYTHONPATH` via `pytest.ini`.
- **Assets flow through `public/`** — renderer copies audio/images/BGM/SFX to `public/` before Remotion render, then cleans up temp files after.
- **snake_case ↔ camelCase boundary** — Python uses snake_case, Remotion/TS uses camelCase. The `renderer.py` converts at the boundary.
- **Per-scene TTS timing** — `generate_voice_with_timing()` returns `scene_timings` (start_ms/end_ms per scene) for precise audio-video sync. Scene ID `-1` is the outro.

### Input Modes

| Mode | Input | Analyzer | Source |
|------|-------|----------|--------|
| `image` | Screenshot file | `analyze(BlindPost)` | Blind OCR |
| `manual` | Title + body text | `analyze(BlindPost)` | Manual entry |
| `url` | Blind URL | `analyze(BlindPost)` | Web scrape |
| `topic` | Free topic text | `analyze_topic(TopicInput)` | User topic |

### Visual Modes

| Mode | Generator | Output | Cost |
|------|-----------|--------|------|
| `manga` | GPT Image API | PNG per scene | ~$0.005/scene |
| `video` | Seedance API | MP4 per scene | ~$0.05/scene |

### Image Styles (manga mode)

| Style | Description |
|-------|-------------|
| `webtoon` | Korean webtoon (default), uses reference images |
| `3d_pixar` | Pixar/Disney 3D render |
| `realistic` | Photorealistic Korean drama style |
| `anime` | Japanese anime style |

## Environment Variables

- `OPENAI_API_KEY` — required for GPT Image generation
- `SEEDANCE_API_KEY` — optional, for AI video clip generation (video mode)
- `SEEDANCE_API_BASE` — optional, Seedance API base URL (default: `https://api.seedance.ai/v1`)

## Recent Changes
- 006: Phase 6 영상 쇼츠 모드 구현 완료
  - 범용 주제 입력 (TopicInput, analyze_topic, TOPIC_ANALYZE_PROMPT)
  - 이미지 스타일 프리셋 4종 (webtoon/3d_pixar/realistic/anime)
  - Seedance API 완전 구현 (generate/poll/download/generate_and_wait)
  - 파이프라인 분기 (topic 모드, manga/video 비주얼 모드)
  - UI: 주제 탭, 비주얼 모드 토글, 이미지 스타일 선택
  - renderer.py: scene_videos 파라미터 + public/ 복사
  - 테스트: 7개 신규/수정 테스트 파일
- 005: Data model extensions (SubtitleStyle, TransitionConfig, SfxConfig)
- 005: scene_ops.py (split, merge, reorder, resize) + API endpoints

## Active Technologies
- Python 3.11+ (백엔드), TypeScript + React (Remotion 영상, Next.js 16 프론트엔드)
- edge-tts, openai, httpx, remotion
- JSON 파일 기반 (`data/raw/`, `data/scripts/`, `data/audio/`, `data/images/`, `data/videos/`)
