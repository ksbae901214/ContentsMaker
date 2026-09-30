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
- **쇼츠 영상은 만들기 전에 버전부터 묻는다 (2026-09-30 사용자 지시)** — 영상 제작 요청이
  오면 기획안을 쓰기 **전에** `AskUserQuestion` 으로 어떤 버전으로 만들지 먼저 묻는다.
  `multiSelect: true` 로 물어 **V2.1+V2.2 병행**(같은 주제 하루 2편, V2.2→유튜브 · V2.1→틱톡,
  034)도 고를 수 있게 한다. 소재를 보고 고른 추천 버전을 첫 선택지에 두고 라벨 끝에
  "(추천)" 을 붙인다. **사용자가 요청에 버전을 이미 적었으면("V4로 만들어줘") 묻지 않는다.**
  각 선택지 설명에는 아래 표의 한 줄 설명을 쓴다.

  | 버전 | 한 줄 설명 | 잘 맞는 소재 | 렌더러 (`format`) |
  |---|---|---|---|
  | **V2.1** | 원본 육성 훅 1컷 + TTS 논평 브리핑 (육성 약 35%) | 인물의 한 마디가 센 소재 · 틱톡용 | `render_political_v2_1.py` (`v2_1`) |
  | **V2.2** | 원본 육성 클립 2~5개 릴레이 + 마지막 TTS 정리 1개 (육성 65% 이상) | 여야·당사자 발언이 영상으로 다 있는 소재 · 유튜브용 | `render_political_v2_2.py` (`v2_2`) |
  | **V3.0** | 인물 1명 프로필 다큐 — 훅만 육성, 무음 B-roll + 전체 TTS, 흰 캔버스·궁서 제목·인물 배지, BGM 없음, 구독형 CTA | 지금 화제인 인물의 이력·배경 | `render_profile_v3.py` (`profile_v3`) |
  | **V4.0** | 영상 없이 사진 슬라이드(3.4초 고정) + 전체 TTS, BGM 없음, **정치 전용**, 완료 시 제목 A/B+3줄요약+해시태그 | 육성 영상이 없는 소재 (SNS 글·성명·기사만 있는 경우) | `render_news_v4.py` (`news_v4`) |

  추천 기준: 육성 영상이 있으면 V2.2(+V2.1 병행) / 인물 소개면 V3.0 / 육성이 없으면 V4.0.
  비정치 소재(경제·사회·연예)에는 V4.0 을 권하지 않는다(렌더러가 차단한다). 레거시 파이프라인
  (027 jpolitics 모먼트 직캠, 030 하이브리드, 009 political-pro 3기획안)은 선택지에 넣지
  않는다 — 사용자가 이름을 대면 그때 쓴다. 버전을 정한 뒤에 039 돌파 3문항과 040 대칭 검토로
  넘어간다.
- **소재 선정은 돌파 3문항이 먼저다 (039)** — 쇼츠를 기획할 때(채팅에서 소재를
  제안하는 경우 포함) 다른 무엇보다 먼저 `scripts/shorts_breakout.py`의 3조건을
  통과시킨다: ①이 사람에게 화내는 데 정치 성향이 필요한가(필요하면 탈락, 민간인
  75% vs 정치인 9%) ②이미 무언가를 잃었는가(사과·취소·사퇴·박탈, 36% vs 7%)
  ③당내 절차인가(제명·재신임·공천·청원·낙선·징계 — **무조건 탈락, 실측 13편 0%**).
  유명 정치인이라는 이유로 소재를 고르지 말 것 — 인물 인지도는 실측상 변수가
  아니다. 한 편이 뚫리면 새 소재보다 **후속을 먼저** 붙인다. 근거표는
  `political_v2_configs/README.md` 039 절.
- **정치편은 한 편 안에서 대칭이어야 한다 (040)** — 실측 133편의 진영 감사는
  여권만 21편(중앙 1,400) / 야권만 22편(1,300) / 양쪽 32편(1,297)로 **채널
  전체로는 이미 균형인데 셋 다 1,300**이다. 균형이 133편 단위로만 있고 한 편
  단위로는 없어서다 — 시청자는 한 편만 본다. 정치 소재는 ①한 편에 양쪽 진영을
  다 넣고 ②같은 잣대로 다루며(코드가 못 잡는다, 눈으로 확인) ③**'과거 발언 vs
  현재 행동'** 프레임을 최우선으로 고른다(정치편 상위가 전부 이 프레임이고 양쪽
  모두에게 성립해 중도 포지션이 자동 유지된다). CTA는 '누구 잘못'이 아니라 판정을
  넘기는 질문으로. 편성 목표는 political 40 / society 25 / entertainment 20 /
  economic 15%(범죄 소재 제외) — `scripts/shorts_symmetry.py`,
  `scripts/shorts_balance.py`, README 040 절.
- **훅 앞에 한 줄 인트로가 기본이다 (V2.1·V2.2, 2026-09-15 사용자 확정)** —
  `scenes[0]` 에 `"intro": true` + 한 문장(4초 이내) 나레이션을 넣으면 그 씬이
  육성 훅보다 **먼저** 나온다. 등장인물이 여럿인 소재(청문회·국정감사)는 맥락
  없이 첫 육성을 틀면 누가 누구에게 하는 말인지 몰라 이탈한다. 036 "훅은 가장
  센 컷"과 맞바꾸는 것이라 **1개·4초 상한**으로 묶었다. 템플릿 5종에 포함,
  누락 시 렌더 경고(차단 아님, 우회 `"intro_gate": "off"`), profile_v3 는 면제
  (`shorts_format.FormatRules.intro_required`). 훅 씬은 나레이션이 없어 TTS
  타이밍에 안 잡히므로 `with_hook_timing()` 이 구간을 명시 주입한다 — 이게
  없으면 훅 자막이 `timestamp=float(sid)` 로 1초에 떠서 인트로를 덮는다.
  상세는 `political_v2_configs/README.md` "intro" 절.
- **Upload package is authoritative for the completion message (038)** — `render_political_v2_1.py`/`_v2_2.py` print a 제목/3줄요약/해시태그 block (`political_upload_package.build_chat_ready_block()`) to stdout right after rendering, and write the same content into `upload_package.md`. When reporting a finished 정치쇼츠 in chat, quote that block verbatim — do not hand-write a new title/summary/hashtags from scratch. This closes a recurring failure (see `[[video-completion-summary-hashtags]]` memory) where the set was omitted or improvised because nothing upstream generated it.
- **CTA 나레이션은 질문까지 읽는다 (V2.1·V2.2 고정 지침, 2026-09-17 사용자 지시)** —
  `cta.voice` 는 선택지만 읽지 말고 **질문 문장을 앞에 붙인다**:
  `"이건 누가 잘못한 걸까요? 1번 노인, 2번 여성. 댓글로 알려주세요."` 035 는 4초
  상한을 아끼려 "질문은 화면 자막이 보여주니 나레이션에선 뺀다"였는데, 쇼츠는
  소리만 듣는 시청자가 많아 번호만 들리면 **무엇을 고르라는 건지 알 수 없다.**
  상한도 4.0 → **5.0초(약 41자)** 로 함께 올렸다(`CTA_MAX_SEC`). 검사는
  `political_cta.lint_cta_question` — 블록 CTA·씬으로 직접 쓴 CTA 양쪽 경로 모두.
  구독형(`cta_style: "subscribe"`, 041 V3.0)은 질문이 아니라 부탁이라 면제.
  **경고이지 차단이 아니다** — 기존 config 51개가 걸리므로 과거 편은 그대로 두고
  신규만 적용한다(035/036/039/040 과 같은 방침).
- **BGM(`emotion_type`)만 바꾸고 싶으면 `highlight_category` 로 강조어 색을 고정한다** —
  036 은 "emotion_type 을 바꿔도 화면은 그대로고 BGM 만 바뀐다"고 했지만 그 약속은
  배경색·자막색에만 해당했고 **강조어 색은 emotion 에 묶여 있었다**(relatable 하늘색
  ↔ touching 분홍 ↔ angry 빨강). V2.1/V2.2 렌더러가 씬의 `highlight_category`
  (`fact` 노랑 / `criticism` 빨강)를 전달하도록 연결했다 — 미지정 `"neutral"` 이면
  기존 동작 그대로다. **어두운 BGM = `touching`** (실측: `touching_2/_3` 는 고역이
  46~53dB 낮아 9개 트랙 중 가장 어둡다. `angry` 는 저역만 크고 고역이 밝아
  '긴장'이지 '어두움'이 아니다).
- **정치쇼츠 BGM 은 어두운 트랙만 — 코드로 고정, config 로 못 끈다 (2026-09-18 사용자 지시)** —
  밝은 BGM 이 규탄 소재를 가볍게 만든다는 지적이 반복돼 지침으로 박았다.
  `emotion_type` 지정으로는 보장이 안 된다: ①`angry` 는 고역이 `relatable_2` 보다
  밝고 ②`touching` 이어도 트랙 번호는 **에너지 점수**(씬 수·강조 비율·길이)가
  고르므로 짧은 편은 `touching_1`(-44.6dB, `relatable_2` 와 사실상 동급)이 걸린다.
  그래서 풀 자체를 좁혔다 — `voice_config.DARK_BGM_FILES`
  (`touching_2`/`touching_3`) + `DARK_BGM_SOURCE_TYPES`(`political_pro`).
  `select_bgm_for_script()` 가 이 source_type 이면 **emotion 을 무시**한다.
  `shorts_domain` 의 political 기본 emotion 도 `touching` 으로 바꿨지만 그건 표시일
  뿐(되돌려도 안 밝아진다). **기존 정치 config 도 재렌더하면 어두워진다** — 035/039/040
  과 달리 "과거는 유지"가 아니다(음악은 소급이 곧 원하는 결과). profile_v3 는
  `USE_BGM=False` 라 무관, 연예·사회·경제는 source_type 이 달라 무변경.
  검증: 렌더 아웃트로 고역 **-64.1 → -83.3dB**, `tests/test_political_dark_bgm.py` 6건.
  상세는 `political_v2_configs/README.md` 마지막 절.

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
- 042 쇼츠 V4.0 사진 슬라이드 뉴스 카드 (2026-09-30, 사용자 확정):
  - 벤치마크 = 경쟁 채널 @gokorea012 틱톡 1편(29.3초). **영상 클립 0개** — 사진을
    **3.4초 고정 타이머**(실측 컷 간격)로 넘기며 줌, 전 구간 Charon TTS, **BGM 없음(코드
    고정)**. `scripts/render_news_v4.py`(validate/photos-sheet/render), 템플릿
    `_template_news_v4.json`, 포맷 키 **`news_v4`**, 상세는 README 042 절.
  - **정치 전용**(category≠political 차단). 사진은 네이버 뉴스·검색 캡처, `photos[*].credit`
    필수(하단 `출처 : A · B` 자동 조립). fact_sources·나무위키 차단은 041 과 동일.
  - **사진과 자막은 다른 시계** — `scripts/news_v4_timeline.py`(순수 함수): photos[0]=첫 문장
    끝까지, 이후 3.4초 고정 / 자막은 나레이션을 어절 경계 16자로 쪼개 글자 수 비례.
    TTS 는 문장 단위 그대로라 Gemini 한도 영향 없음. 사진 누락은 **TTS 전에** 차단.
  - Remotion: `NewsCardLayer.tsx` 신규(1080 정사각 박스 y=440, 검정 자막 박스, 회색 출처 줄)
    + 옵트인 프롭 `newsCard`/`headlinePlain`/`badgeBoxed`. 제목은 배민 도현(`BM Dohyeon`).
    **기존 4종 still 8장 변경 전후 바이트 동일.**
  - 같은 채널을 025 에 벤치마크한 `src/jpolitics/` 와 무관(당시는 노란 헤드라인+클립).
  - **완료 블록 = 자극적 제목 A/B + 3줄요약 + 해시태그** (2026-09-30 사용자 지시) —
    `render` 가 `news_v4_chat_block()` 을 출력하고 채팅엔 그 블록을 그대로 인용한다.
    config 에 `yt_title`·`yt_title_alt`(공포·충격·호기심 톤, 명사로 닫기)·`hashtags` 3~4개를
    적는다 — 누락 시 경고. 1호 DMZ 지뢰×김여정 편(`20260930_dmz_mine_kimyj_news_v4.json`) 렌더 완료.
  - 미착수: Phase E(사진 수집 보조) · `render --reuse-tts`(지금은 TTS 캐시를 429 때만 읽어 재렌더마다 Gemini 1회 소모).
- 041 쇼츠 V3.0 인물 프로필 다큐멘터리 — Phase A (2026-09-14, 사용자 확정):
  - 외부 지침(Click Shortform "뉴스 3.0") 2종을 이 레포의 V2.1 파이프라인 위로
    옮긴 신규 포맷. **`scripts/render_profile_v3.py`**, 템플릿
    `_template_profile_v3.json`, 상세 규격은 `political_v2_configs/README.md` 041 절.
  - ⚠️ **이름 충돌** — 레포에 이미 "V3"가 둘 있다(`src/jpolitics/` 027 모먼트 직캠,
    `src/analyzer/hybrid_*` 030 하이브리드). 신규 포맷은 **항상 `profile_v3`**.
  - **V2.1 의 확장이지 새 파이프라인이 아니다.** 사용자가 오디오를 "훅만 육성"으로
    확정한 덕에 오디오 조립이 V2.1 `hook` 블록(무음 패딩 + 타이밍 시프트)과 동일
    구조가 됐다 — 새 오디오 코드 0. 씬 컷·길이 캡·업로드 패키지 전부 재사용.
  - 사용자 확정 4건: ①**정치인 프로필**(지침 원문) ②**훅만 육성**(절충)
    ③**V3.0에만 궁서체** ④**구독·댓글 유도형 CTA**(지침 원문).
    **①④는 채널 실측과 반대 방향이다** — 차단하지 않고 계측으로 판정한다(아래).
  - `scripts/shorts_format.py` (신규) — frozen `FormatRules` × 3 포맷
    (`v2_1`/`v2_2`/`profile_v3`) + 포맷 원장. 036 카테고리 원장과 **같은 파일**을
    쓰되 항목을 **병합**한다(덮어쓰면 먼저 쓴 축이 조용히 사라진다).
    **포맷은 제목으로 추론하지 않는다** — 제목만으로 V2.1/V2.2/V3.0 구분이 불가능해
    원장에 없는 과거 편은 `unknown`(legacy). 틀린 추론은 파일럿 근거를 오염시킨다.
  - 게이트 3종을 포맷 인지화: **040 진영 대칭 침묵**(인물 1명이라 개념상 성립 안 함),
    **039 경고를 1회 고지로**(정치인 인물편은 기본 C등급 — 매 편 3줄씩 붙으면
    게이트 전체가 무시당한다. **당내 절차 DEAD 는 유지**), **`cta_style: "subscribe"`**
    로 선택지형 요구만 면제(존댓말 종결·4초 상한은 그대로 — 말투 규칙은 포맷 무관).
  - **차단 신설 2건 (법적 요건)**: `fact_sources` 누락 · **나무위키 URL**.
    V2.2 는 화면의 육성이 인용이라 그 자체가 방패인데 V3.0 은 나레이션 전체가 채널
    자신의 서술이라 방패가 없다. 나무위키는 CC BY-NC-SA 라 celebrity 모드가 업로드를
    코드로 막아 둔 것과 같은 이유로 **업로드용 근거로 못 쓴다**. 우회 `"fact_gate": "off"`.
  - Remotion 옵트인 2종: `PersonBadge.tsx`(우상단 실명+직책, 아웃트로 전까지),
    `TitleBar` 에 `fontFamily`/`letterSpacing` 프롭. **미지정이면 037 규격(Noto
    100px) 그대로** — still 프레임 비교로 V2 렌더 결과가 **바이트 동일**임을 확인.
  - 디자인 실측 확정: macOS `GungSeo` 는 **Regular 단일 웨이트**(→3px 외곽선으로 보강),
    궁서는 자폭이 넓어 10자만 넘어도 줄이 접히고 **3줄이 되면 인물 배지를 덮는다**
    → 각 줄 `nowrap` + 72~100px 자동 축소 + 줄당 12자 경고. 2줄 투톤(1열 흰색 /
    2열 `#E50914`)은 지침의 딥 차콜 투톤을 이 레포 캔버스(클립 위 반투명 검정)에 맞춘 것.
  - 도입 안 함: Google Drive 자동 업로드·Zero Disk(로컬 보관이 이 레포 표준),
    원본 100% 음소거(사용자 절충), Whisper 전사(037 VTT 방식으로 대체 예정),
    `zoompan`+`trim` 절단(Remotion 은 프레임 기반이라 그 버그가 구조적으로 없다).
  - **낭독 톤·흰 캔버스 (2026-09-14 추가 지시)**:
    - "V3.0 속도를 V2.1과 같게" → 확인해 보니 **`tts_speed` 는 원래부터 양쪽 다
      1.1 로 같았다.** 체감 속도를 가른 건 Gemini TTS 의 **style_prompt** 다 —
      `calm documentary narration` 은 같은 대본에서 타임라인 50.8초,
      `fast newscaster`(V2.1 문구)는 **35.7초**. Gemini TTS 속도는 배속이 아니라
      이 문구로 맞춘다. 지침의 다큐 톤보다 채널 일관성을 택했다.
    - 지침 §4-1 흰 캔버스(`#F5F5F5`)는 **레이어 세 겹**을 다 바꿔야 한다:
      ①`ShortsComposition` 의 `isPoliticalPro` 강제 검정(`respectBackgroundColors`
      옵트인) ②`SceneWithVideo` 의 `background:"#000"`(`canvasColor` 프롭)
      ③**`cut_segment` 의 `pad=...:black`** — 패딩 색이 **클립 파일에 구워진다**.
      ③은 캔버스가 검정이던 시절 배경과 구분이 안 돼 아무도 몰랐던 것이고,
      흰 배경으로 바꾸는 순간 검은 띠로 드러난다. + 밝은 캔버스에서는
      `SceneWithVideo` 의 dark overlay 도 생략(자막이 레터박스 밖에 있어 목적 없음).
    - **기본값은 전부 기존 동작** — `respect_background_colors=False` /
      `canvasColor="#000"` / `pad_color="black"`. V2.1/V2.2·dem_shorts 무변경.
  - **V3.0 고정 규격 3건 (2026-09-14 사용자 지시)**:
    - **BGM 없음** — `render_profile_v3.USE_BGM = False` 로 **코드 고정**(config 로
      켤 수 없다). 인물 프로필은 나레이션이 전부라 BGM 이 낭독을 덮는다.
      **036 의 `emotion_type` = BGM 스위치 규칙은 V3.0에 적용되지 않는다**
      (emotion_type 은 자막·배경색 기본값으로만 남는다). V2.1/V2.2 무변경.
      검증은 나레이션 없는 아웃트로 구간 음량으로 — 없음 **-91.0dB**(무음) vs
      있음 -31.7dB (`ffmpeg -sseof -3.5 -i x.mp4 -af volumedetect -f null -`).
    - **헤드라인 1열·인물 배지 = 딥 차콜 `#111111`** — 흰 캔버스에서 흰 글자는
      박스 없이는 안 보인다. 지침 §3-1 투톤(딥 차콜/비비드 레드)을 그대로 적용.
    - **제목·배지의 반투명 검정 박스 제거** — 흰 캔버스에서 회색 박스로 보인다.
      출처 라벨의 박스는 지시 범위 밖이라 유지. 궁서 3px 외곽선은 유지(어두운
      글자에서 합성 볼드 역할).
    - 렌더 프롭 `headline_color`/`overlay_boxes` — 기본값은 기존 동작(흰색·박스
      유지)이라 V2.1/V2.2 무변경.
  - 검증: pytest **1969 passed / 1 skipped**(신규 114), 변경 파일 ruff 통과
    (`renderer.py` 의 `DATA_AUDIO_DIR` 미사용 import 1건은 HEAD 부터 있던 것),
    tsc 통과, **기존 config 112개 스캔 = 차단 4건·경고 284건으로 변경 전과 완전 동일**.
  - **Phase B(소싱 자동화)는 미착수** — 039 실측상 정치인 인물편이 불리한 축이라
    1호 검증이 먼저다. 판정: profile_v3 8~10편 중앙값이 political 1,255회를 넘고
    society/인물 논란(1,912/2,200)대에 접근하는가. 실패 시 조정 순서는 ①인물 범위
    (정치인 → 화제의 비정치 인물) ②CTA(구독형 → 선택지형).
- 040 중도 상품화 + 편성 비중 (2026-09-04, 채널 실측 133편, 사용자 확정):
  - **문제**: 어제 업로드분이 청주 교권 627회 / 박위–전장연 1,600회로 죽었다.
    둘 다 039 게이트(민간인·대가)는 통과했다. 게이트가 못 보는 축이 있었다.
  - **진단 ①(중도)** — 제목 진영 감사: 여권만 21편 1,400 / 야권만 22편 1,300 /
    양쪽 32편 1,297. 인물별로도 국민의힘 39 / 이재명 27 / 민주당 21 / 장동혁 13.
    **이미 균형인데 셋 다 1,300이다.** 균형이 133편 단위로만 존재하고 한 편
    단위로는 없다 — 시청자는 한 편만 본다.
  - **진단 ②(벤치마크)** — 구독자 대비 쇼츠 중앙: 슈카월드 10.4% / 김지윤의
    지식Play 4.8%(중도·설명형)가 진영 채널 9곳(0.1~3.8%)을 전부 이긴다.
    무인칭 사건 채널 1분현상수배는 구독자 295명에 중앙 6,400(2,170%).
    내 채널은 515명에 1,850(359%) — **제작이 아니라 장르가 천장**이다.
  - **진단 ③(편성)** — political 88편 66% 중앙 1,200 vs society 8편 1,912 /
    인물 논란 23편 2,200. 중앙값이 높은 축이 편성의 6~17%뿐이다.
  - `scripts/shorts_symmetry.py` (신규) — frozen `SymmetryVerdict` +
    `sides_in()`/`evaluate_symmetry()`/`symmetry_warnings()`. 진영 사전(여/야) +
    `BOTH_MARKERS`('여야') + `RECORD_CONTRAST_WORDS`('과거 발언 vs 현재 행동').
    **정치 카테고리에만** 적용하고 사전 미검출이면 침묵(오탐 방지).
    config 키 `"symmetry_gate": "off"`.
  - `scripts/shorts_balance.py` (신규) — `TARGET_MIX` political 40 / society 25 /
    entertainment 20 / economic 15%(**범죄 제외**, 사용자 확정). 036 카테고리
    원장의 `recorded_at` 순 최근 20편으로 재고 목표 ±10%p 초과 시 경고.
    표본 8편 미만이면 침묵. config 키 `"balance_gate": "off"`.
  - **판정 범위** — 제목 + 씬 자막(`text`)만. 나레이션 제외 — 039 `frame_text`
    와 같은 이유로 대칭은 화면에 보여야 시청자 판단에 반영된다.
  - 반영: `render_political_v2_1.py` `config_warnings()`(v2.2도 재사용),
    `shorts_domain.py` 정치 체크리스트 4항목 + 판정형 `cta_example`,
    `political_planner_stage_a_prompt.py` 2개 프롬프트, README 040 절, `CLAUDE.md`.
  - **경고, 차단 아님** (035/036/039와 같은 방침). 기존 config 87개 스캔 =
    **차단 0건**, 정치 59개 중 55개 경고(양쪽 24 / 여권만 16 / 야권만 10 /
    미검출 9). 과거 유지·신규만 적용. 검증: pytest **1855 passed / 1 skipped**
    (신규 41), 변경 파일 ruff 통과.
  - **한계**: 중도 설명형 성공 사례(김지윤·슈카)는 **둘 다 진행자 인물이 있다.**
    무인칭 중도 설명형은 벤치마크에 사례가 없다 — 빈 자리이자 검증 안 된 자리다.
    '판정을 시청자에게 넘긴다'(한문철TV 모델, 구독자 대비 중앙 59,000)가 그
    인물 자리를 대신한다는 게 가설이다. **파일럿 10편 뒤 political 중앙값이
    society/인물 논란(1,912 / 2,200)을 따라 올라오는지로 판정한다.**
- 039 돌파 조건 — 소재 선정 3문항 (2026-09-03, 채널 실측 130편):
  - **문제**: 조회수가 1,000~2,200 밴드에 갇혀 있고 3,000회 이상은 16편(12%)뿐.
    정치 87편의 중간 50%가 1,000~1,700. 소재·인물·언어·제목 유형을 87번 바꿔도
    분포가 안 흔들렸다 — **편차를 만드는 건 제작 품질이 아니라 소재 조건**이다.
    인물 인지도는 변수가 아니다(이재명 20편 1,224 / 장동혁 16편 1,300 /
    오세훈 9편 1,300 / 한동훈 9편 1,000), 언어판도 무관(한글 1,200 / 영문 1,300).
  - **돌파 3조건** — ①진영 밖 인물인가(민간인 75% vs 정치인 9%, 정치인은 정책이
    아니라 반칙이면 25%) ②이미 대가를 치렀는가(36% vs 7%) ③당내 절차인가
    (**13편 전멸 0%** — ②를 갖춰도 ③을 어기면 죽는다: 장동혁 제명 위기 1,500 /
    조국 징역 2년 1,471 / 이진숙 복귀 반전 581 / 장동혁 재신임 조건 **16회**).
  - `scripts/shorts_breakout.py` (신규) — frozen `BreakoutVerdict` + `evaluate()` +
    `breakout_warnings()`. 등급 A(민간인 75~83%) / B(정치인+반칙 25%) /
    C(미충족 7%) / DEAD(당내 정치 0%). config 키 `subject_type`
    (civilian/politician/institution) · 우회 `"breakout_gate": "off"`.
  - **판정 범위** — ②(대가)는 제목+씬 자막, **③(당내·진행중)은 제목만**.
    씬 자막까지 봤더니 `joguk_bangbae_v2_1`('조국은 왜 방배동을 안 팔까', 개인
    위선 소재)이 자막의 "어제 전당대회 영상 축사" 한 단어로 DEAD가 됐다.
    소재의 정체는 제목이 정한다. 자막에만 당내 어휘가 있으면 등급은 유지하고
    별도 경고만 띄운다.
  - **당사자 추정** — 명시값 > 직함 > **036 카테고리**. 직함 없는 정치인 이름
    ("용혜인 내로남불")을 민간인으로 오판하면 게이트가 조용히 통과시켜 버린다.
    정치 카테고리인데 당사자가 민간인인 편은 `subject_type`을 직접 박을 것.
  - **증폭기**: 뚫린 소재는 후속도 뚫린다(박위 55,523→7,002→6,208,
    용혜인 4,226→3,300→3,149). 밴드 안 소재의 후속은 그대로 밴드 안
    (조국 1,471→1,248) — 한 편이 뚫리면 새 소재보다 후속이 먼저다.
  - **경고, 차단 아님** (035/036과 같은 방침). 기존 config 83개 스캔 =
    C 56 / A 16 / B 7 / DEAD 4, 과거 유지·신규만 적용.
  - **한계**: ③은 13편 전멸이라 강하나 ①②는 민간인 표본 8~11편이고 박위 3편이
    포함돼 83%는 "6편 중 5편"이다. 전부 조회수만 본 결과라 **돌파편이 노출을 더
    받은 것인지 같은 노출에서 안 넘긴 것인지 미상**(리텐션·CTR 미계측).
  - 반영: `shorts_breakout.py`, `shorts_domain.py` 공통 체크리스트 1항목,
    `render_political_v2_1.py` `config_warnings()`, `political_planner_stage_a_prompt.py`
    3개 프롬프트, `political_v2_configs/README.md` 039 절, `CLAUDE.md`.
    검증: pytest **1814 passed / 1 skipped**(신규 31), 변경 파일 ruff 통과.
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
