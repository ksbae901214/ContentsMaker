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
python3 -m src.main image screenshot.png [screenshot2.png ...]  # Screenshot → video
python3 -m src.main image screenshot.png --no-bgm --no-references  # Disable BGM / reference images
python3 -m src.main manual --file data/raw/x.json  # JSON → video
python3 -m src.main manual --interactive           # Interactive prompt entry
python3 -m src.main url https://gall.dcinside.com/...  # URL → video (DCInside / Nate Pann / Naver Cafe)
python3 -m src.main analyze --file data/raw/x.json [--with-tts]  # Analyze only
python3 -m src.main tts --file data/scripts/x.json   # TTS only
python3 -m src.main render --script data/scripts/x.json --audio data/audio/x.mp3  # Render only
python3 -m src.main pipeline --file data/raw/x.json  # Full pipeline
python3 -m src.main freepik_login                  # One-time Freepik browser login
python3 -m src.main deevid_login                   # One-time deevid.ai browser login
python3 -m src.main youtube-auth                   # One-time YouTube OAuth
python3 -m src.main tiktok-auth                    # One-time TikTok OAuth

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
    → Freepik/GPT Image API → manga PNGs (data/images/)   [manga mode]
    → Freepik/deevid/Seedance → video clips MP4 (data/videos/)  [video mode]
    → edge-tts → voice MP3 + timing JSON (data/audio/)
      → Remotion render → MP4 (data/outputs/)
        → YouTube / TikTok upload (optional)
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
| `video_gen/` | AI video generation | `seedance_gen.py` (API), `deevid_gen.py` (browser automation, Veo 3.1), `factory.py` (provider selection), `base.py` (abstract) |
| `editor/` | Scene editing | `scene_ops.py` (split/merge/reorder/resize), `batch.py`, `project.py`, `translator.py`, `template.py` |
| `upload/` | Platform upload | `youtube_uploader.py` (YouTube Data API v3 resumable upload), `tiktok_uploader.py`, `metadata_generator.py` (auto-generates title/description/tags/hashtags from `ShortsScript`) |
| `config/settings.py` | Global paths & constants | `PROJECT_ROOT`, `DATA_*_DIR`, `CLAUDE_TIMEOUT_SECONDS=1800`, `MAX_SCENE_DURATION_SECONDS=5.0` |

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
- **Shared prompt guards** — `src/illustrator/image_constants.py` (NO_TEXT_GUARD / PHOTO_STYLE_PREFIX / PHOTO_STYLE_FOOTER / ANATOMY_GUARD) and `src/video_gen/motion_prompt_builder.py` (`build_motion_prompt`) are the **single source of truth** for image/video prompt guards. Both the web UI (`app/api/generate/route.ts`) and any e2e scripts must import from these modules, not duplicate the guards locally.
- **snake_case ↔ camelCase boundary** — Python uses snake_case, Remotion/TS uses camelCase. The `renderer.py` converts at the boundary.
- **Per-scene TTS timing** — `generate_voice_with_timing()` returns `scene_timings` (start_ms/end_ms per scene) for precise audio-video sync. Scene ID `-1` is the outro.
- **Max scene duration** — `MAX_SCENE_DURATION_SECONDS=5.0` enforced at script generation time. Pre-existing scripts can be split with `scene_ops.split_scenes_to_max_duration()`. This ensures each scene fits within one Kling 2.5 / Wan 2.2 / MiniMax clip (shortest common ceiling across Premium+ unlimited models).
- **Reference images** — webtoon-style image generation reads from `data/references/`. Pass `--no-references` to skip.

### Input Modes

| Mode | Input | Analyzer | Source |
|------|-------|----------|--------|
| `image` | Screenshot file | `analyze(BlindPost)` | Blind OCR |
| `manual` | Title + body text | `analyze(BlindPost)` | Manual entry |
| `url` | URL | `analyze(BlindPost)` | DCInside / Nate Pann / Naver Cafe scrape |
| `topic` | Free topic text | `analyze_topic(TopicInput)` | User topic |

### Visual Modes

| Mode | Generators | Output | Cost |
|------|-----------|--------|------|
| `manga` | Freepik (Nano Banana Pro / GPT 1.5 / Flux.2 Max) **or** OpenAI GPT Image API | PNG per scene | $0 (Premium+ unlimited) or $0.005/scene (GPT API) |
| `video` | Freepik (Kling 2.5 / MiniMax / Wan 2.2) **or** deevid.ai **or** Seedance API | MP4 per scene | $0 (Premium+ unlimited) or free (deevid 20 credits) or $0.05/scene (Seedance) |

### Image Providers (manga mode)

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| `freepik` (default) | Browser automation (Playwright) | $0 on Premium+ (`FREEPIK_IMAGE_MODEL_PRIORITY` = Nano Banana Pro → GPT Image 1.5 → Flux.2 Max) | Run `python3 -m src.main freepik_login` once |
| `gpt` | OpenAI API | $0.005/image, supports reference images for consistent style | `OPENAI_API_KEY` env var |

`FreepikImageGenerator` reuses a single browser session for all N scene images — selects model + 9:16 once, then clears/retypes the prompt per scene. On model failure it falls back down the priority list. Selectors in `src/illustrator/freepik_image_selectors.py`.

### Video Providers (video mode)

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| `freepik` (default) | Browser automation (Playwright) | $0 on Premium+ (`FREEPIK_VIDEO_MODEL_PRIORITY` = Kling 2.5 → MiniMax Hailuo 2.3 Fast → Wan 2.2) | Run `python3 -m src.main freepik_login` once |
| `deevid` | Browser automation (Playwright) | Free (20 credits, Veo 3.1) | Run `python3 -m src.main deevid_login` once |
| `seedance` | API | ~$0.05/scene 720p | `SEEDANCE_API_KEY` env var |

**Premium+ unlimited**: Kling 2.5 720p, MiniMax Hailuo 2.3 Fast, Wan 2.2 are unlimited under the Freepik Premium+ plan ($34/month annual) — monthly 90-clip goal (3 videos/day × 30 days) stays at $0 variable cost. The generator tries each model in priority order, falling back on per-scene failures.

**Model slug discovery**: `MODEL_DATA_CY` in `freepik_selectors.py` maps 41 video models and `IMAGE_MODEL_DATA_CY` in `freepik_image_selectors.py` maps 29 image models to their stable `ai-model-item-<slug>` data-cy attributes. To update after UI change: run `freepik_login`, open the All models modal, and inspect `data-cy` via DevTools.

### Image Styles (manga mode)

| Style | Description |
|-------|-------------|
| `webtoon` | Korean webtoon (default), uses reference images |
| `3d_pixar` | Pixar/Disney 3D render |
| `realistic` | Photorealistic Korean drama style |
| `anime` | Japanese anime style |

## Environment Variables

- `OPENAI_API_KEY` — required for GPT Image generation (only if using `provider='gpt'`)
- `SEEDANCE_API_KEY` — optional, for Seedance API video provider
- `SEEDANCE_API_BASE` — optional, Seedance API base URL (default: `https://api.seedance.ai/v1`)
- (no env vars needed for `freepik` or `deevid` providers — they use persistent browser profiles at `.cache/freepik_profile/` and `.cache/deevid_profile/`)
- YouTube upload requires `data/.youtube_credentials.json` (OAuth 2.0 Desktop App client secret from Google Cloud Console → YouTube Data API v3). Token saved to `data/.youtube_token.json` after `youtube-auth`.

## Recent Changes
- 010: Cost guard — prevents accidental Premium+ credit usage
- 009: `MAX_SCENE_DURATION_SECONDS=5.0` enforced; `scene_ops.split_scenes_to_max_duration()` added so Kling 2.5 clips never freeze
- 008: Freepik Premium+ 무제한 최적화
  - 영상: `MODEL_DATA_CY` 맵 41개 모델 + `_select_model()` + 폴백 체인 (Kling 2.5 → MiniMax → Wan 2.2)
  - 이미지: `FreepikImageGenerator` 신규 — 1 세션 N 이미지 + Nano Banana Pro 무제한 + `_generate_via_freepik()` 분기
  - UI: 만화 모드에 `imageProvider` 토글 (freepik/gpt)
  - Freepik 세션 없으면 GPT로 자동 폴백
  - 월 90편 변동비 $0 (Premium+ $34/월 고정비만)
  - 18개 신규 테스트 (228 total passing), Next.js 빌드 통과
  - E2E 검증: Kling 2.5 영상 50초 생성, Nano Banana Pro 이미지 2장 140초 생성
- 007: Phase 7 deevid.ai 브라우저 자동화 (Veo 3.1)
  - DeevidGenerator (Playwright 기반, generate_and_wait 오버라이드)
  - deevid_selectors.py (UI selector 외부화)
  - factory.py에 deevid 등록 (lazy import)
  - `python3 -m src.main deevid_login` CLI 추가
  - UI: videoProvider 토글 (deevid / seedance)
  - 12개 신규 테스트 (197 total passing)
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
