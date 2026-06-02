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
python3 -m src.main celebrity "손흥민"              # Celebrity intro short (학습 목적 전용)
python3 -m src.main celebrity "세종대왕" --no-video  # Skip Freepik, use still images
python3 -m src.main celebrity "유재석" --no-images  # Gradient background only
python3 -m src.main freepik_login                  # One-time Freepik browser login
python3 -m src.main deevid_login                   # One-time deevid.ai browser login
python3 -m src.main gemini_login                   # One-time Gemini web login (Imagen 4 / Veo 3)
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
| `scraper/` | Content ingestion | `image_extractor.py` (OCR), `topic_input.py` (free-topic input); `gemini_youtube_transcriber.py` (Phase 1A: Gemini Files API transcript, fallback to Whisper) |
| `analyzer/` | AI script generation | `claude_analyzer.py` (`analyze()` + `analyze_topic()`); `gemini_backend.py` (Phase 1B: Gemini 2.5 Flash alt backend, toggled via `ANALYZER_BACKEND`); `notebooklm_style.py` (Phase 3B: multi-source → 2-speaker script); `political_fact_checker.py` (Phase 4: Gemini Grounding fact-check) |
| `illustrator/` | Manga image generation | GPT Image API (`gpt-image-1`); `gemini_web_image_gen.py` (Phase 2A: Imagen 4 via gemini.google.com web), 4 image styles (webtoon/3d_pixar/realistic/anime) |
| `tts/` | Voice synthesis | `edge-tts` (free, async); `gemini_multi_voice.py` (Phase 3A: dual-speaker Charon anchor + Kore reporter); `voice_config.py` maps emotion → voice/colors/gradient |
| `video/` | Video rendering | `renderer.py` wraps Remotion CLI; copies images/videos/audio to `public/` |
| `video_gen/` | AI video generation | `seedance_gen.py` (API), `deevid_gen.py` (browser automation, Veo 3.1), `gemini_web_video_gen.py` (Phase 2B: Veo 3 via gemini.google.com web), `factory.py` (provider selection), `base.py` (abstract) |
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
| `political` | YouTube URL + timestamps | `analyze_political(PoliticalInput)` | YouTube download + VTT |
| `political_pro` | YouTube URL | `generate_three_plans` + `plan_to_script` | RTF 6요소 3 기획안 비교 → 1 선택 → 검수 → 영상 (Feature 009) |
| `celebrity` | Person name | `analyze_celebrity(CelebrityInfo)` | Namuwiki scrape + Naver images (학습 목적 전용) |

### Visual Modes

| Mode | Generators | Output | Cost |
|------|-----------|--------|------|
| `manga` | Freepik (Nano Banana Pro / GPT 1.5 / Flux.2 Max) **or** OpenAI GPT Image API | PNG per scene | $0 (Premium+ unlimited) or $0.005/scene (GPT API) |
| `video` | Freepik (Kling 2.5 / MiniMax / Wan 2.2) **or** deevid.ai **or** Seedance API | MP4 per scene | $0 (Premium+ unlimited) or free (deevid 20 credits) or $0.05/scene (Seedance) |

### Image Providers (manga mode)

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| `freepik` (default) | Browser automation (Playwright) | $0 on Premium+ (`FREEPIK_IMAGE_MODEL_PRIORITY` = Nano Banana Pro → GPT Image 1.5 → Flux.2 Max) | Run `python3 -m src.main freepik_login` once |
| `gemini` | Browser automation (Playwright) | $0 on Pro (Imagen 4 via gemini.google.com; ~10 images/day estimated) | Run `python3 -m src.main gemini_login` once |
| `gpt` | OpenAI API | $0.005/image, supports reference images for consistent style | `OPENAI_API_KEY` env var |

Fallback chain for image: `gemini` → `gpt` → gradient background.

`FreepikImageGenerator` reuses a single browser session for all N scene images — selects model + 9:16 once, then clears/retypes the prompt per scene. On model failure it falls back down the priority list. Selectors in `src/illustrator/freepik_image_selectors.py`.

### Video Providers (video mode)

| Provider | Type | Cost | Setup |
|----------|------|------|-------|
| `freepik` (default) | Browser automation (Playwright) | $0 on Premium+ (`FREEPIK_VIDEO_MODEL_PRIORITY` = Kling 2.5 → MiniMax Hailuo 2.3 Fast → Wan 2.2) | Run `python3 -m src.main freepik_login` once |
| `gemini` | Browser automation (Playwright) | $0 on Pro (Veo 3 via gemini.google.com; 8s 720p + native audio; Phase 2B) | Run `python3 -m src.main gemini_login` once |
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
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` — required for `celebrity` mode image search (free, 25,000 req/day). Register at https://developers.naver.com/apps/ → 애플리케이션 등록 → 검색
- `GEMINI_API_KEY` — required for `political_pro` mode (Gemini TTS Charon voice) and Phase 1A/1B/3A/4 Gemini API features. Free tier: 5 RPM, 10 req/day. Get key at https://aistudio.google.com/app/apikey. **Quota fallback**: 429 RESOURCE_EXHAUSTED 발생 시 `data/tts_cache/{hash}.mp3`(콘텐츠 해시 캐시) 또는 `data/audio/*{slug}*.mp3`(제목 매칭 폴백)에서 자동 재사용. 성공한 호출은 자동 캐시.
- `ANALYZER_BACKEND` — `"claude"` (default) or `"gemini"` to switch script analysis to Gemini 2.5 Flash (Phase 1B). Free tier: 250 req/day.
- (no env vars needed for `freepik`, `deevid`, or `gemini` web providers — they use persistent browser profiles at `.cache/freepik_profile/`, `.cache/deevid_profile/`, `.cache/gemini_profile/`)
- YouTube upload requires `data/.youtube_credentials.json` (OAuth 2.0 Desktop App client secret from Google Cloud Console → YouTube Data API v3). Token saved to `data/.youtube_token.json` after `youtube-auth`.

## Celebrity Mode (Phase 9) — Legal Notice

The `celebrity` mode uses **Namuwiki** (CC BY-NC-SA 3.0) and **Naver Image Search** (third-party images). Generated videos are for **personal learning use only**.

Hard requirements enforced in code:
- `CelebrityInfo.source_url` must be a `https://namu.wiki/...` URL (`src/scraper/celebrity_models.py:28`)
- `analyze_celebrity()` overrides `source_type="celebrity"` + `source_url=namu.wiki URL` regardless of Claude output (`src/analyzer/celebrity_analyzer.py:70`)
- The Claude prompt forbids verbatim Namuwiki quotes and mandates "출처: 나무위키" in the last scene (`src/analyzer/celebrity_prompt.py`)
- YouTube/TikTok upload UI is **hidden** on the celebrity tab (`app/page.tsx`)

Do not enable the upload toggles or post these videos publicly without verifying Naver image copyright + subject publicity rights independently.

## Recent Changes
- 014: Gemini 통합 Phase 1A–4 (초안, 미통합)
  - Phase 1A: `gemini_youtube_transcriber.py` — Gemini Files API로 transcript 추출 (Whisper 대체, 20~40초). 폴백 체인: VTT → Gemini → Whisper.
  - Phase 1B: `gemini_backend.py` — `ANALYZER_BACKEND=gemini` 으로 분석 백엔드를 Gemini 2.5 Flash로 교체. 기본값은 `claude` (14일 안정성 검증 후 전환 예정).
  - Phase 2A: `gemini_web_image_gen.py` — Imagen 4 (gemini.google.com 웹 자동화). 폴백: gemini → gpt → 그라데이션. `gemini_login` CLI 추가.
  - Phase 2B: `gemini_web_video_gen.py` — Veo 3 (gemini.google.com 웹 자동화, 8s 720p + 네이티브 오디오). Phase 2B 초안 — selector 확인 필요.
  - Phase 3A: `gemini_multi_voice.py` — Charon(앵커) + Kore(패널) 2인 TTS. `--multi-voice` 플래그로만 활성화; 락인 포맷(단일 Charon) 보호.
  - Phase 3B: `notebooklm_style.py` — 복수 URL/PDF/텍스트 → Gemini 2.5 Flash → 2인 대화형 쇼츠 스크립트.
  - Phase 4: `political_fact_checker.py` — Gemini Grounding + Google Search로 정치 발언 팩트체크. 🟢/🟡/🔴 배지 + 출처 첨부 (100 grounded queries/일 무료).
  - 신규 Gemini selectors: `gemini_web_selectors.py` (이미지·영상 공용 selector 외부화).
- 013: 정치 숏츠 V2 (Feature 011 Phase B) — Remotion 시각 연출 강화. Scene 모델에 `subtitle_color`/`subtitle_emphasis`/`visual_layout`/`secondary_clip_path` 추가. plan_to_script가 Narration의 자막 색을 Scene으로 매핑 + visual_directives의 "분할/split" 키워드 자동 검출 → 매칭 씬에 layout=split. SceneText.tsx에 V2 색·강조 적용 (yellow/red/blue/white + 1.4x 폰트). 신규 SplitScreenScene 컴포넌트(상·하 분할, 각 1080x960). Hook/CTA 씬은 자동 yellow+emphasis. e2e: 8씬 30초 영상에 7가지 색·강조·split 모두 적용 확인.
- 012: 정치 숏츠 V2 (Feature 011 Phase A) — "잘나가는 정치 유튜버" 지침(MBC 라디오 시사 + 뉴스핌TV) 반영. ShortsPlan에 `format_type` (A=인터뷰/논평, B=현장 밀착) + `format_reason` + `visual_directives`(좌·우 분할 등 시각 연출 지시) 추가. Narration에 `subtitle_color` (white/red/yellow/blue) + `subtitle_emphasis` 추가. Stage A 프롬프트에 A/B 자동 분류 가이드 + 예시. Stage B 프롬프트에 자막 색 프리셋 + 시각 연출 지시 + "댓글 고래잡기" 강화 CTA. V1 plans.json 호환 유지(default fallback). 영상 렌더는 Phase B에서 적용 예정.
- 011: Political Shorts Planner (Feature 009) — RTF 6요소 3 기획안 + Gemini TTS Charon (정치 모드)
  - 신규: `political_pro` 모드 (탭 + API + CLI `python3 -m src.main political-pro`)
  - 3 기획안 Claude 단일 호출, angle 3종(title_anchor / audience_resonance / comparison)
  - Gemini TTS Charon voice + Newscaster style (British RP, Rapid, Temp 0.5) — `style_prompt` + `temperature` 파라미터 추가
  - 원본 9:16 클립 + Remotion 렌더 (변동비 $0)
  - FR-020 자동 업로드 차단 (백엔드 강제 가드), FR-021 검수 필수 경고 배너
  - 33 신규 테스트 통과
- 010: Cost guard — prevents accidental Premium+ credit usage
  - 영상: `MODEL_DATA_CY` 맵 41개 모델 + `_select_model()` + 폴백 체인 (Kling 2.5 → MiniMax → Wan 2.2)
  - 이미지: `FreepikImageGenerator` 신규 — 1 세션 N 이미지 + Nano Banana Pro 무제한 + `_generate_via_freepik()` 분기
  - UI: 만화 모드에 `imageProvider` 토글 (freepik/gpt)
  - Freepik 세션 없으면 GPT로 자동 폴백
  - 월 90편 변동비 $0 (Premium+ $34/월 고정비만)
  - 18개 신규 테스트 (228 total passing), Next.js 빌드 통과
  - E2E 검증: Kling 2.5 영상 50초 생성, Nano Banana Pro 이미지 2장 140초 생성
  - DeevidGenerator (Playwright 기반, generate_and_wait 오버라이드)
  - deevid_selectors.py (UI selector 외부화)
  - factory.py에 deevid 등록 (lazy import)
  - `python3 -m src.main deevid_login` CLI 추가
  - UI: videoProvider 토글 (deevid / seedance)
  - 12개 신규 테스트 (197 total passing)
  - 범용 주제 입력 (TopicInput, analyze_topic, TOPIC_ANALYZE_PROMPT)
  - 이미지 스타일 프리셋 4종 (webtoon/3d_pixar/realistic/anime)
  - Seedance API 완전 구현 (generate/poll/download/generate_and_wait)
  - 파이프라인 분기 (topic 모드, manga/video 비주얼 모드)
  - UI: 주제 탭, 비주얼 모드 토글, 이미지 스타일 선택
  - renderer.py: scene_videos 파라미터 + public/ 복사
  - 테스트: 7개 신규/수정 테스트 파일

## Active Technologies
- Python 3.11+ (백엔드), TypeScript 5.x + React 19 / Next.js 16 (프론트엔드 + API 라우트), Remotion 4.x (영상 렌더링) + Claude Code CLI (분석), `google-genai` (Gemini TTS, 기존 import), `yt-dlp` + `openai-whisper` (영상/자막), `ffmpeg` (클립 cut), `playwright`(기존 다른 모드용, 본 기능에서는 미사용) (009-political-pro-planner)
- 로컬 JSON/MP4 파일 (`data/political_pro/{timestamp}_{slug}/` — 영상·transcript·plans 보관, `data/scripts/` — 검수 가능한 ShortsScript, `data/outputs/` — 최종 MP4). 데이터베이스 없음. (009-political-pro-planner)
