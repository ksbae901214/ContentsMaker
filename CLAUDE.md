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
python3 -m pytest tests/dem_shorts/ -v        # Dem-Shorts subsystem tests
python3 -m pytest tests/jpolitics/ -v         # 정치쇼츠 V3 subsystem tests

# Frontend component tests (Vitest + jsdom)
npm run test:ui                          # Runs app/components/__tests__/**

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
python3 -m src.main political-pro <YouTube URL>    # 정치 숏츠: 3 기획안 비교 → 검수 → 영상 (Feature 009)
python3 -m src.main political-pro <YouTube URL> --hybrid  # V3 하이브리드: 원본 발언 50% + TTS 논평 50% (Feature 030)
python3 -m src.main daily-briefing                 # 어제(KST) 정치 이슈 수집 → 클러스터링 → 점수화 → 기획안
python3 -m src.main cleanup                         # data/ 산출물 정리 (src/maintenance/cleanup.py)
python3 -m src.main gems list                       # Gemini Gems 프리셋 목록
python3 -m src.main gems show-prompt webtoon --kind image  # Gem 지침 텍스트 출력 (붙여넣기용)

# Subsystem CLIs (own entry points, NOT under src.main)
python3 -m src.jpolitics.main run <YouTube URL>    # 정치쇼츠 V3 모먼트 직캠 (detect/cut/render, Feature 027)
python3 -m src.dem_shorts.cli db-init              # Dem-Shorts Studio: SQLite 마이그레이션 + seed
python3 -m src.dem_shorts.cli poll-natv            # NATV 채널 폴링 → source_videos upsert (그 외 download/score/stt/diarize/gate ...)

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

1. **Web UI** (`app/`): Next.js 16 app. The general-pipeline generation endpoint is `POST /api/generate` (SSE progress). Major feature subsystems mount their own UI + API: `app/jpolitics/` (정치쇼츠 V3), `app/dem-shorts/` (Dem-Shorts Studio), `app/daily-briefing/` (Daily Briefing), plus `app/api/political-pro/`, `app/api/lawmaker/`, etc.
2. **CLI** (`src/main.py`): main Python CLI — `image`, `manual`, `url`, `analyze`, `tts`, `render`, `pipeline`, `celebrity`, `political-pro`, `daily-briefing`, `cleanup`, `gems`, plus `*-login` / `*-auth`. Two subsystems have **separate** CLI entry points: `python3 -m src.jpolitics.main` and `python3 -m src.dem_shorts.cli`.

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
| `jpolitics/` | 정치쇼츠 V3 (Feature 027) | Self-contained: `main.py` CLI (detect/cut/render/run), `analyzer/moment_detector.py`, `models/`, `video/` (clip_maker, captions, renderer), `api_bridge.py` for the web UI. "모먼트 직캠" — detect viral moments in a YouTube clip → cut → Remotion render |
| `briefing/` | Daily Briefing | `naver_news_collector.py` + `youtube_collector.py` → `issue_clusterer.py` → `scorer.py` → `plan_runner.py`. Collects yesterday's (KST) political issues, clusters, scores, drafts plans. Frozen dataclasses in `models.py` |
| `dem_shorts/` | Dem-Shorts Studio | Largest subsystem, **SQLite-backed** (`db/` + migrations). Pipeline: source collection → STT (`diarization.py`) → speaker ID → `scoring.py` (dem_score) → `ranking/` (Google Trends / Naver DataLab / Wikipedia / YouTube metrics) → `compliance/` gate (election guard + keyword/LLM guardrails) → `editor/` → `renderer.py`. Own CLI `cli.py`, frozen dataclasses in `models/` |
| `maintenance/` | Housekeeping | `cleanup.py` — prunes `data/` artifacts (backs the `cleanup` CLI command) |
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
- **Per-scene SFX is globally OFF (soft-disabled 2026-06-12, commit `8c1bfef`)** — `renderer.py` forces `enable_sfx=False`/`auto_sfx=False`, `app/api/generate` & `rerender` pin `useSfx=false` and ignore the client toggle, and the SFX `<Audio>` block is removed from `ShortsComposition.tsx`. Assets/code are preserved for re-enable: `Scene.sfx` field, `SfxConfig`, `src/video/sfx_matcher.py`, `SfxPicker.tsx`, `data/sfx/`, `public/sfx/`. Do not "re-wire" SFX unless explicitly asked; see `prompt_plan.md` (029) for the rationale and re-enable steps.
- **Shared prompt guards** — `src/illustrator/image_constants.py` (NO_TEXT_GUARD / PHOTO_STYLE_PREFIX / PHOTO_STYLE_FOOTER / ANATOMY_GUARD) and `src/video_gen/motion_prompt_builder.py` (`build_motion_prompt`) are the **single source of truth** for image/video prompt guards. Both the web UI (`app/api/generate/route.ts`) and any e2e scripts must import from these modules, not duplicate the guards locally.
- **snake_case ↔ camelCase boundary** — Python uses snake_case, Remotion/TS uses camelCase. The `renderer.py` converts at the boundary.
- **Per-scene TTS timing** — `generate_voice_with_timing()` returns `scene_timings` (start_ms/end_ms per scene) for precise audio-video sync. Scene ID `-1` is the outro.
- **Max scene duration** — `MAX_SCENE_DURATION_SECONDS=5.0` enforced at script generation time. Pre-existing scripts can be split with `scene_ops.split_scenes_to_max_duration()`. This ensures each scene fits within one Kling 2.5 / Wan 2.2 / MiniMax clip (shortest common ceiling across Premium+ unlimited models).
- **Reference images** — webtoon-style image generation reads from `data/references/`. Pass `--no-references` to skip.
- **Upload package is authoritative for the completion message (038)** — `render_political_v2_1.py`/`_v2_2.py` print a 제목/3줄요약/해시태그 block (`political_upload_package.build_chat_ready_block()`) to stdout right after rendering, and write the same content into `upload_package.md`. When reporting a finished 정치쇼츠 in chat, quote that block verbatim — do not hand-write a new title/summary/hashtags from scratch. This closes a recurring failure (see `[[video-completion-summary-hashtags]]` memory) where the set was omitted or improvised because nothing upstream generated it.

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
- 039 하루 3편 자동 제작·업로드 (2026-08-26, 사용자 지시):
  - **신규 패키지 `scripts/auto_daily/`** — 07:00 정치 / 12:00 경제 / 18:00 연예.
    앞 두 슬롯은 전날 소재, 저녁은 당일 소재. **기존 렌더러는 한 줄도 수정하지 않는다**
    — 이 패키지는 `render_political_v2_2.py` 앞단의 config 생산자다.
    상세: `scripts/auto_daily/README.md`.
  - 파이프라인: `topic_ranker`(댓글수/조회수 랭킹) → `source_finder`(yt-dlp 검색 +
    채널 화이트리스트) → `cut_planner`(자동자막 단어 타임스탬프 → 문장 경계 컷, 037-2)
    → `config_drafter`(Claude 초안 + 게이트 3회 재시도) → 기존 렌더러 →
    `review_gate` → `upload_shorts` → `notify`.
  - **게이트를 새로 만들지 않았다** — `validate_config`/`config_warnings` 를 그대로
    호출한다. 두 벌이 되면 034 보도체·035 길이·036 도메인 게이트가 조용히 갈라진다.
  - **확정 정책 3가지** (사용자 선택): ①**초기 2주 전면 보류** — 렌더까지 무인,
    업로드 직전 정지(`data/auto_daily/review_policy.json`). 저작권 스트라이크가
    채널을 날릴 수 있는 유일한 항목이라 여기가 안전판. ②**TikTok 은 초안까지만** —
    `privacy_level: "SELF_ONLY"` 고정, 공개 게시는 심사 통과 앱만. ③config 는
    **LLM 초안 1개 + 게이트 루프**(무수정 통과율 <50%면 3안 제시 방식으로 전환).
  - **원본은 URL 로 고정** — `config_drafter._force_provenance` 가 `sources.main.url`
    에 정확한 영상 URL 을 박는다. 검색어를 남기면 렌더러 download 가 같은 검색으로
    **다른 영상**을 받아 모든 컷이 엉뚱한 구간을 가리킨다(렌더는 성공, 내용만 틀림).
  - **자동화되지 않는 것**: 게시 승인 / TikTok 게시(1탭) / **댓글 고정**(YouTube
    Data API v3 에 고정 엔드포인트가 없다 — 작성까지만 자동) / 훅 품질.
  - **선행 작업**: `data/auto_daily/channel_policy.json` 의 `allow` 등록(비어 있으면
    전 슬롯 보류 — 의도된 기본값), `youtube-auth`, `tiktok-auth`.
  - 검증: pytest **2003 passed / 1 skipped**(신규 227), 변경 파일 ruff 통과.
- 038 업로드 패키지 자동화 강화 + CTA 위치 변경 (2026-08-25, 사용자 지시):
  - **3줄요약 자동 생성** — `political_upload_package.py`에 `build_three_line_summary(cfg)`
    신규. `upload_package.md`에 애초에 3줄요약 섹션이 없었던 게 반복 누락의 원인이었다
    (assistant가 매번 파일에도 없는 요약을 기억만으로 새로 써서 채팅에 붙이다 3회 누락 —
    `[[video-completion-summary-hashtags]]` 메모리). `cfg["hook"]["text"]`(v2.1) 또는
    `scenes[0]["text"]`(v2.2, 훅이 clip 씬)를 1줄, 본문 중 최장 자막을 2줄, 마지막
    비-CTA 씬 자막을 3줄로 뽑는다. `voice`(TTS 나레이션) 대신 `text`(화면 자막) 기준 —
    v2.2 clip 씬은 원본 육성이라 `voice`가 없다.
  - **렌더 완료 시 콘솔에 세트 전체 출력** — `render_political_v2_1.py`/`_v2_2.py`가
    `upload_package.md` **경로만** 찍던 것을 `build_chat_ready_block()`(제목·3줄요약·
    해시태그)까지 stdout에 출력하도록 변경. 렌더 완료 메시지는 이 블록을 그대로
    인용한다(직접 재작성 금지) — Key Conventions에 규칙 추가.
  - **제목 자극성 강화** — `political_planner_stage_a_prompt.py`의 3개 STAGE_A
    프롬프트(정치/토픽/경제)에 "제목 톤" 절 추가, 공포·충격·호기심 단어를 기본값으로
    명시(`[[shorts-title-sensational-tone]]` 메모리 반영). `gate_yt_title`(보도체 금칙
    어미)과는 별개 게이트라 충돌 없음.
  - **CTA를 마지막 씬으로 되돌림** — `political_cta.py`의 `apply_cta()`가 035에서 도입한
    40% 지점 삽입을 그만두고 항상 `scenes` 끝에 CTA를 붙인다. 035 결정(당시 댓글율
    0.24% 실측, "CTA가 끝에 있으면 도달 자체가 안 된다")을 뒤집는 것 — 사용자가
    "CTA가 중간에 나오는 게 싫다"고 명시적으로 지시. 변경 후 댓글율 재확인 권장(강제 아님).
    `cta_insert_index()`/40% 관련 로직은 향후 재사용 대비 보존, `apply_cta()`만 미사용.
  - 반영: `political_upload_package.py`, `render_political_v2_1/2.py`, `political_cta.py`,
    `political_planner_stage_a_prompt.py`, `CLAUDE.md`, `political_v2_configs/README.md`
    035/2절, `prompt_plan.md` 038 절. 상세 계획: `prompt_plan.md`.
- 037 제작 규격 고정 — **제목 100px · 클립은 말 끝맺음까지** (2026-08-25, 사용자 지시):
  - **제목 폰트 크기 = 100px 고정** — `src/video/remotion/src/ShortsComposition.tsx` 의 `TitleBar`
    (`fontSize: 100`, 서체는 기본 `Noto Sans KR` 유지). 75px 기본값은 쇼츠 피드에서 제목이 안 읽힌다.
    **자막(`SceneText`)은 건드리지 않는다** — 자막을 키우면 방송 번인 자막과 겹치고, 한 줄 글자 수가
    줄어 `WebkitLineClamp:3` 이 `…`로 자른다 (검은고딕 135px 을 자막에 시도했다가 전 씬이 3줄로
    밀려 폐기).
  - **`mode: "clip"` 씬은 문장 끝 단어가 다 발화된 뒤 끊는다** — 어미가 잘리면 시청자가 말이 끊긴
    것으로 인지해 이탈한다. **눈대중·auto-caption 블록 타임스탬프 금지**(롤링 자막이라 문장 경계와
    안 맞는다). `yt-dlp --write-auto-subs` 로 VTT 를 받아 `<00:00:12.345><c>단어</c>` 인라인
    **단어 단위 타임스탬프**로 잡는다. `duration` = 마지막 단어 시작 + 발화 길이(= 다음 단어 시작).
    다음 문장 첫 단어가 물리면 그 직전에서 끊는다.
  - **끝맺음 때문에 42초 캡을 넘기면 `duration_gate` 를 끄지 말고 씬을 하나 뺀다** — 정보량이 가장
    낮은 씬(속편이면 전편 복습 씬)이 1순위.
  - **원본에 박힌 자막 카드도 눈으로 확인** — 방송 클립은 카드와 나레이션이 최대 6초 어긋난다.
    발화가 맞아도 카드가 다른 문장이면 자막과 어긋나 보인다. 카드가 소재와 무관한 채널
    (뉴스 낭독 + 무관한 스트리밍 화면)이나 서술이 단정적인 채널은 소스에서 뺀다.
  - **버그 수정**: `renderer.py` 가 프롭을 camelCase 로 바꾸는데 `SceneText` 는 `font_size` 등
    snake_case 만 읽어 **CLI 렌더 경로에서 `subtitle_style` 이 통째로 무시되고 있었다.** 양쪽 다
    읽도록 수정 (웹 Player 경로는 변환을 안 타서 snake_case 로 도착).
  - 반영: `shorts_domain.py` 공통 체크리스트 1항목, `political_v2_configs/README.md` 037 절,
    `ShortsComposition.tsx`, `SceneText.tsx`. 검증: pytest 1773 passed / 1 skipped.
- 운영 지침 — **CTA 나레이션은 "댓글로 알려주세요"로 닫는다** (2026-08-18, 사용자 지시):
  - CTA는 영상에서 유일하게 시청자에게 **직접 말을 거는** 문장이다. 나머지가 전부 존댓말인데 CTA만 `"번호로 답글."` 같은 명사형·반말로 끊으면 부탁이 아니라 지시로 들린다.
  - **실패 사례**: 장동혁 '올공데이' 편(`jang_olgongday_v2_1/v2_2`)이 `"1번 결집, 2번 고립. 번호로 답글."`로 렌더돼 나갔다. 템플릿 5종이 전부 이 종결을 물고 있었고 검사가 없었다.
  - **사각지대가 두 겹이었다** — ① `lint_cta`가 선택지형·길이만 보고 말투는 안 봤고, ② 2026-08-14 지시로 CTA를 **마지막 씬에 직접 쓰는 게 표준**이 되면서 `lint_cta`가 보는 top-level `cta` 블록 경로를 요즘 config가 아예 안 탄다.
  - **4초(약 32자) 상한과 충돌한다** — 종결 문구가 9자를 먹어 남는 건 약 23자. 질문은 화면 자막이 이미 보여주므로 나레이션에선 빼고 선택지만 읽는다: `"1번 조국, 2번 이준석. 댓글로 알려주세요."`
  - 반영: `political_cta.py` — `CTA_CLOSING` + `lint_cta_closing()`(블록 경로) + `scene_cta_closing_warnings()`(씬 직접 작성 경로, 자막에 `①`/`1번`이 박힌 씬만 CTA로 판정해 오탐 방지), `config_warnings()` 연결. 템플릿 5종 + `DEFAULT_PINNED_COMMENT` + README 035 절 + `shorts_domain.py` 체크리스트 1항목.
  - **차단이 아니라 경고** — 기존 config 12개가 걸려 하드 게이트로 올리면 재렌더가 막힌다(035 길이 캡과 같은 방침: 과거 유지, 신규만 적용). 검증: pytest **1773 passed / 1 skipped**(신규 9), 변경 파일 ruff 통과.
- 036 운영 지침 — **훅(scenes[0])은 가진 클립 중 가장 센 컷** (2026-08-13, 사용자 지시):
  - 사연이 있는 소재는 시간순 배열이 자연스러워 보이지만, 그러면 **상황 설명이 앞에 오고 절정이 뒤로 간다.** 클립을 다 잘라 놓고 세기 순으로 재정렬해 1등을 `scenes[0]`에 놓는다. 순서를 바꿔 문맥이 깨지면 자막이 메운다 — 훅이 약한 것보다 낫다.
  - **실패 사례**: 경제 1호(`bigeoju_1jutaek_v2_2.json`)가 씬0을 기자 나레이션("손주 돌보러 이사")으로 두고, 진짜 훅("제가 투기꾼입니까?" + 국민참여입법 의견 화면)을 씬1에 뒀다.
  - **경제의 절정은 표정이 아니라 '내 돈이 걸린 한 문장'** — 034의 "클립 1순위 = 표정·리액션 절정"은 정치 기준이다. 경제는 화자가 당국자·기자·전문가라 표정이 없다. 훅 우선순위: ①당사자 1인칭 항의·반문 ②화면에 숫자·문구가 박힌 컷 ③당국자의 말 바꾸기·후퇴 ④(최후) 기자 나레이션 — 여기까지 내려오면 소재를 다시 볼 것.
  - 반영: `README.md` 편집 규칙 + 036 절, `shorts_domain.py` economic 체크리스트 1항목, `_template_economic_v2_2.json` scene0 주석. 검증: pytest 51 passed, ruff 통과.
- 036 운영 지침 — BGM(emotion_type) 선택 · 연예는 V2.2만 (2026-08-13):
  - **`emotion_type` = 사실상 BGM 스위치**. BGM은 `select_bgm_for_script`가 `emotion_type` 하나로만 고른다(`data/bgm/<emotion>_N.mp3`). V2.1/V2.2는 배경색을 `bg_colors`, 자막색을 씬별 `color`로 따로 지정하므로 **emotion_type을 바꿔도 화면은 그대로고 BGM만 바뀐다** — 소재 톤에 맞춰 config에 직접 지정할 것.
  - **실패 사례**: 하영 증조부 친일 논란 편이 연예 기본값 `funny`를 물려받아 **`funny_2.mp3`(코믹 BGM)**로 렌더됨. 카테고리 기본값은 소재의 톤을 모른다.
  - 선택 기준 — 사실전달·중립 `relatable` / 대립·규탄 `angry` / 비극·서사 `touching` / 축하·가벼움 `funny`(**논란 소재 금지**). 카테고리 기본값: political `angry` / economic `relatable` / society `touching` / entertainment `funny`.
  - 템플릿 3종에 `emotion_type`을 명시 항목으로 추가(경제 `relatable` / 사회 `touching` / 연예 `relatable`) — 기본값을 무심코 물려받지 않도록.
  - **연예쇼츠는 V2.2만 제작**(사용자 확정). V2.1은 영상의 65%가 TTS 논평이라 연예 소재에서 논평이 곧 단죄로 읽히고 명예훼손 노출이 크다. 034 플랫폼 분리에서 연예의 V2.1(틱톡) 자리는 비운다.
- 036 카테고리 확장 Phase 1~3 — 도메인 규칙 팩·가드레일·템플릿 (2026-08-13):
  - `scripts/shorts_domain.py` (신규) — frozen `DomainRules` × 4 카테고리. 결과어/공방어·CTA 예시·고정댓글·제목 앵커·emotion/배경색·금지어·주의어·체크리스트를 한 표로. 정치 규칙은 `political_upload_package`의 기존 상수를 **그대로 참조**(두 곳이 갈라지면 035 게이트가 조용히 약해짐).
  - **가드레일 2단** — 차단(`gate_domain_words`→ValueError): 경제 투자권유 13종(매수·매도·추천주·존버·물타기…, 유사투자자문 소지). 경고(`domain_warnings`): 사회 피의사실 / 연예 미확인 사생활 / 경제 전망 표현 / 연예 `source_channel` 누락. 둘 다 `"domain_gate": "off"` 우회.
  - **관통** — `lint_topic_frame`·`is_clash_frame`·`has_outcome_frame`·`lint_yt_title`·`resolve_pinned_comment`·`build_upload_package_md`(체크리스트), `lint_cta(cta, category)`, 렌더러 `resolve_emotion_type`/`resolve_bg_colors`(config 명시값 우선).
  - **템플릿 3종** — `_template_{economic,society,entertainment}_v2_2.json`. 카테고리별 배경: 경제 청록/relatable, 사회 남색/touching, 연예 보라/funny.
  - **주의**: 034 보도체 게이트(`~했다` 과거형 어미 차단)는 카테고리 공통 — 경제·연예 제목도 과거형으로 끝내면 렌더가 막힌다. 명사로 닫을 것.
  - 검증: pytest **1764 passed / 1 skipped**(신규 106), ruff 통과, **기존 정치 config 37개 전부 차단 0·경고 0·렌더 기본값 변화 0**. Phase 4(파일럿)는 운영 작업.
- 036 카테고리 확장 Phase 0 — 정치 외 경제·사회·연예 계측 (2026-08-13):
  - **결정**: 새 파이프라인 없이 **V2.2 표준에 `category` 축 관통**. 렌더러·38~42초 캡·릴레이 구조·CTA 삽입은 도메인 무관. 사용자 확정 — 단일 채널 혼합, 경제→사회→연예 순, 이번엔 Phase 0(계측)만.
  - `scripts/shorts_category.py` (신규) — 카테고리 원장 `data/channel_analytics/category_ledger.json`(권위) + 제목 키워드 추론(폴백, 한/영). 제목 매칭은 NFC·해시태그 제거·공백 축약 + **접두 일치**(업로드 시 붙는 해시태그·꼬리말 흡수). 추론은 `classify_title`과 달리 **해시태그를 신호로 사용**(주제 메타데이터이므로).
  - `political_upload_package.py` — `upload_package.md` 카테고리 표기 + 렌더 시 원장 자동 기록(`generate_upload_package(..., ledger_path=)`). 기록 실패는 경고만.
  - `analyze_channel_performance.py` — `summarize(entries, ledger=)`에 `by_category`, 리포트 카테고리 표 + `category_mix_warnings()`(표본 3편 이상, 전체 중앙값 <70% 희석 / ≥130% 확대), `--ledger` 옵션.
  - `render_political_v2_1/2.py` — `validate_config`에서 category 오타 fail-fast. **미지정 = `political`** 이라 기존 config 31개 무변경.
  - **기준선(88편 백필)**: political 73편 1,174 / economic 11편 1,172 / society 2편 948 — 전부 전체 중앙값 100% 언저리 = 카테고리로는 아직 차이 없음. 미분류 2%.
  - 검증: pytest **1713 passed / 1 skipped**(신규 55), 변경 파일 ruff 통과. Phase 1~4(도메인 규칙 팩·가드레일·템플릿·파일럿)는 미착수 — `prompt_plan.md` 036 참조.
- 035 조회수/댓글 개선 — 길이 캡·중반 CTA·소재 프레임 (2026-08-05):
  - **근거**: 채널 실측 88편 — 조회수 중앙값 1,169회에 900~1,400 구간이 47%(41편) 집중. 제목 유형(hook 1,151/neutral 1,200/report 1,121)·언어(한글 1,150/영어 1,151)·길이 구간 모두 차이 없음 → 병목은 클릭이 아니라 **완주율**. 최근 18편 좋아요 2.56%/댓글 0.24%(건강 기준의 절반 이하).
  - `scripts/political_length.py` (신규) — 38~42초 캡. `validate` 단계는 글자 수 추정 경고(1.0배속 7.4자/초, 기존 config 31개 × 렌더 결과로 보정, 오차 ±15%), `render` 단계는 실측 타임라인으로 **하드 차단**(Remotion 렌더 전 fail-fast). 우회: config `"duration_gate": "off"`.
  - `scripts/political_cta.py` (신규) — top-level `cta` 블록을 **40% 지점**(가장 가까운 씬 경계)에 tts 씬으로 자동 삽입. scene[0](훅) 앞·마지막 씬 뒤에는 삽입 금지. 편 가르는 선택지형(①/②·1번/2번·누구 잘못·어느 쪽·찬성/반대) 아니면 경고, CTA 나레이션 4초(약 32자) 상한, 일반 씬에 "댓글" 잔존 시 경고.
  - `scripts/political_upload_package.py` — `is_clash_frame`/`has_outcome_frame`/`lint_topic_frame` 추가(공방형 제목 경고), `resolve_pinned_comment`(명시값 > `cta.voice` > 기본값), `DEFAULT_PINNED_COMMENT` 선택지형으로 교체, 체크리스트 035 3항목 추가.
  - `src/analyzer/political_planner_stage_a_prompt.py` — 소재 프레임을 **'결과가 난 사건'**으로 전환. 폐기된 `[악역]-[응징동사]-[주인공]` 공식 제거, 클립 구간 25~40초 + 42초 캡 명시.
  - `render_political_v2_1.py`/`_v2_2.py` — `load_config`에서 `apply_cta` → 검증 → `config_warnings` 출력, `cmd_render`에서 `enforce_length`.
  - 템플릿·README 갱신. 검증: pytest **1655 passed / 1 skipped**, 변경 파일 ruff 통과. 기존 config 31개 중 23개가 캡 초과(과거 파일은 유지, 신규만 캡 적용).
- 030 조회수 개선 P1/P3/P4 (2026-07-03):
  - **P1 제목 엔진**: `ShortsPlan.yt_title: str = ""` 신규 필드. Stage A 프롬프트에 "[악역]-[응징]-[주인공]" 15~30자 훅 제목 규칙. `plan_to_script()`: `yt_title or topic` 우선.
  - **P3 탈보도체**: "보도체 한 문장 (~했습니다 고정)" → "대립 서사체 (주장→반박→역공 아크, 다양한 문말 허용)". `STAGE_B_SYSTEM_PROMPT` / TOPIC / ECONOMIC 3종 갱신.
  - **P4 길이 단축**: 나레이션 4~7개 (22~35초), CTA 2초, 총 40초 캡.
- 030 정치쇼츠 V3 하이브리드 포맷 — Phase D/E 완료 (2026-07-03):
  - `src/analyzer/hybrid_plan_models.py` — `HybridBeat`/`HybridShortsPlan`/`ThreeHybridPlansResult` 완성
  - `src/analyzer/hybrid_planner.py` — `generate_three_hybrid_plans()`: Gemini Stage A → Claude Stage B × 3 angles
  - `src/video/hybrid_renderer.py` — `render_hybrid_shorts()`: per-beat Gemini Charon TTS + ffmpeg concat. edge-tts 폴백.
  - `src/main.py` — `political-pro --hybrid` 플래그: V3 하이브리드 파이프라인 분기 (미지정 시 V2 보존)
  - `tests/test_hybrid_plan_models.py` — 51 tests (HybridBeat·HybridShortsPlan 검증/직렬화 round-trip)
  - **웹 UI 토글 (2026-07-03)**: `app/api/political-pro/hybrid-plans/route.ts` (신규) + `app/components/HybridPlanPicker.tsx` (신규) + `app/page.tsx` (V2/V3 토글·HybridPlanPicker) + `app/api/generate/route.ts` (`hybridMode=on` → `render_hybrid_shorts()`)
  - 검증: pytest 1458 passed / 0 failed, Next.js build 49/49
- 010-jpolitics-v3-isolated: Added Python 3.11+ (백엔드), TypeScript 5.x + React 19 / Next.js 16 (프론트엔드), Remotion 4.x (영상 렌더링, 독립 패키지)
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
  - 신규: `political_pro` 모드 (탭 + API + CLI `python3 -m src.main political-pro`)
  - 3 기획안 Claude 단일 호출, angle 3종(title_anchor / audience_resonance / comparison)
  - Gemini TTS Charon voice + Newscaster style (British RP, Rapid, Temp 0.5) — `style_prompt` + `temperature` 파라미터 추가
  - 원본 9:16 클립 + Remotion 렌더 (변동비 $0)
  - FR-020 자동 업로드 차단 (백엔드 강제 가드), FR-021 검수 필수 경고 배너
  - 33 신규 테스트 통과
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
- Python 3.11+ (백엔드), TypeScript 5.x + React 19 / Next.js 16 (프론트엔드), Remotion 4.x (영상 렌더링, 독립 패키지) (010-jpolitics-v3-isolated)
- 로컬 JSON/MP4 파일 (`data/jpolitics/{ts}_{slug}/` — 영상·plans·script 보관, `data/politician_cards/{name}.json` — 인물 카드 캐시, `data/jpolitics_reference/` — 채널 샘플 키프레임). 데이터베이스 없음. (010-jpolitics-v3-isolated)
