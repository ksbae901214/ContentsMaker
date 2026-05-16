# Implementation Plan: Political Shorts Planner (정치 숏츠 기획자)

**Branch**: `009-political-pro-planner` | **Date**: 2026-05-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-political-pro-planner/spec.md`

## Summary

정치 YouTube 영상 URL을 받아 RTF 영상생성지침 6요소(주제·후킹·구간·흐름·나레이션·CTA) 구조의 **3개 기획안**을 Claude 단일 호출로 생성하고, 사용자가 1개를 선택하면 ShortsScript로 변환 → 검수 화면 → 원본 9:16 클립 + Gemini TTS(Charon, 영국식 RP 아나운서 톤)로 30~60초 MP4를 출력한다.

핵심 기술 접근(research.md 결정 반영):
- **Claude 1회 호출**로 3개 plan을 한 번에 받음(직렬 호출은 90초 SC-001 위반).
- **Gemini TTS** 기존 `gemini_tts_generator.py` 확장(voice="Charon", style_prompt, temperature=0.5).
- **사용 구간은 Claude가 직접 선택** (`select_best_clip` 미사용 — 3개 angle 다양성 확보).
- 기존 `ScriptReviewer` + `segment_cutter.cut_segment` + Remotion 렌더 그대로 재사용.

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript 5.x + React 19 / Next.js 16 (프론트엔드 + API 라우트), Remotion 4.x (영상 렌더링)
**Primary Dependencies**: Claude Code CLI (분석), `google-genai` (Gemini TTS, 기존 import), `yt-dlp` + `openai-whisper` (영상/자막), `ffmpeg` (클립 cut), `playwright`(기존 다른 모드용, 본 기능에서는 미사용)
**Storage**: 로컬 JSON/MP4 파일 (`data/political_pro/{timestamp}_{slug}/` — 영상·transcript·plans 보관, `data/scripts/` — 검수 가능한 ShortsScript, `data/outputs/` — 최종 MP4). 데이터베이스 없음.
**Testing**: pytest (Python 단위/통합), Next.js `npm run build` (타입 체크 + 빌드 검증), 수동 e2e (영상 1편 실행)
**Target Platform**: 로컬 개발자 머신 (macOS/Linux) + Node 22+ + Python 3.11+. 데모는 `localhost:3000`. 배포 대상 없음(개인 운영).
**Project Type**: Hybrid web application — Next.js 16 frontend + Python backend (subprocess 호출), 단일 git repo.
**Performance Goals**: 사용자 입력 → 3개 기획안 표시까지 평균 **90초 이내** (SC-001). 검수 완료 → 최종 영상까지 추가 2분 이내. 무료 한도 안에서 변동비 $0 (SC-007).
**Constraints**: 영상 30~60초(SC-003), 씬당 ≤5초(`MAX_SCENE_DURATION_SECONDS=5.0`), 9:16 세로(1080x1920 또는 720x1280), Gemini TTS 무료 한도(5 RPM) 안, Claude CLI 1회 호출 30s~3min, transcript 처리 상한 30분(research R5).
**Scale/Scope**: 개인 사용 — 동시 사용자 1명, 일일 5~10개 영상 생성, 단일 가족·취미 운영. 외부 트래픽 처리 요구 없음.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 평가 | 메모 |
|------|------|------|
| **I. Zero-Cost Pipeline** | ⚠️ **PARTIAL** | TTS로 edge-tts 대신 Gemini TTS 사용(원칙 글자 위배), 단 **무료 한도 안에서 변동비 $0** — 원칙의 본질 만족. Complexity Tracking #1에 정당화. |
| **II. Pipeline Integrity** | ✅ PASS | 각 단계가 JSON으로 교환, 한 단계 실패 시 명시적 오류(FR-003/008/019) — 환각 차단. |
| **III. Text-First Video** | ✅ PASS | 후킹·나레이션·CTA가 텍스트 중심. 9:16, 30~60초, 최소 32px 텍스트 가독성 기준 그대로 적용. |
| **IV. Content Safety & Legal** | ⚠️ **PARTIAL** | 본 기능은 명시적으로 정치 콘텐츠 처리 — 원칙 IV의 "정치/종교 자동 스킵" 위배. 단 (a) 사용자가 의도적으로 시작 (b) 2단계 검수 (c) 자동 업로드 차단(FR-020) (d) 안전 프롬프트 4종(FR-007) — 자동 파이프라인이 아니므로 원칙의 본래 의도 위배 아님. Complexity Tracking #2에 정당화. |
| **V. Emotion-Driven Experience** | ✅ PASS | ShortsScript의 `emotion_type` 4종 유지(angry/touching/relatable 등), 감정별 색상·BGM 시스템 그대로 재사용. |
| **VI. Modularity & Immutability** | ✅ PASS | 모든 신규 데이터 모델 `frozen=True`, 신규 파일 모두 단일 책임(`political_plan_models.py` 모델만 / `political_planner.py` 로직만 / `political_planner_prompt.py` 프롬프트만). 800줄 한도 안에 충분. |
| **VII. Evidence-Based Completion** | ✅ PASS (필수 실행) | 완료 시 (a) `pytest tests/test_political*.py` 결과 (b) `npm run build` 결과 (c) **테스트 영상 자동 생성** (사용자 메모리 `feedback_test_video.md` 준수) (d) 최종 MP4 경로·길이 첨부 의무. quickstart.md 검증 체크리스트 사용. |
| **VIII. Full Test Gate** | ✅ PASS (필수 실행) | 커밋 전 `python3 -m pytest tests/ -v` 전체 통과 의무. |

**결정**: 게이트 통과(원칙 I·IV 부분 위배는 Complexity Tracking에서 정당화). Phase 0 진행.

## Project Structure

### Documentation (this feature)

```text
specs/009-political-pro-planner/
├── plan.md              # 본 파일
├── research.md          # Phase 0 (완료)
├── data-model.md        # Phase 1 (완료)
├── quickstart.md        # Phase 1 (완료)
├── contracts/           # Phase 1 (완료)
│   ├── api-political-pro-plans.md
│   ├── api-generate-political-pro.md
│   └── cli-political-pro.md
├── checklists/
│   └── requirements.md  # spec 품질 체크리스트 (이미 작성됨)
└── tasks.md             # Phase 2 — /speckit.tasks 가 생성 (본 명령에서는 생성 안 함)
```

### Source Code (repository root)

```text
ContentsMaker/
├── src/                                  # Python 백엔드
│   ├── analyzer/
│   │   ├── political_plan_models.py      # 신규 — ShortsPlan, Narration, ThreePlansResult
│   │   ├── political_planner.py          # 신규 — generate_three_plans, plan_to_script
│   │   ├── political_planner_prompt.py   # 신규 — RTF 6요소 + 절대 준수 4항목 프롬프트
│   │   ├── clip_selector.py              # 기존 — 본 기능에서는 미사용 (Claude가 직접 결정)
│   │   ├── claude_analyzer.py            # 기존 — Claude CLI 호출 패턴 참조
│   │   └── script_models.py              # 기존 — ShortsScript (source_type에 "political_pro" 추가)
│   ├── scraper/
│   │   └── youtube_downloader.py         # 기존 — download_video, transcribe_video_or_fallback 그대로
│   ├── tts/
│   │   └── gemini_tts_generator.py       # 수정 — style_prompt + temperature 파라미터 추가
│   ├── dem_shorts/editor/
│   │   └── segment_cutter.py             # 기존 — cut_segment 9:16 변환 재사용
│   ├── video/
│   │   └── renderer.py                   # 기존 — Remotion 렌더 그대로
│   ├── main.py                           # 수정 — `political-pro` 서브커맨드 추가
│   └── config/settings.py                # 기존 — DATA_DIR/{political_pro} 활용
│
├── app/                                  # Next.js 16 프론트엔드 + API
│   ├── page.tsx                          # 수정 — "political_pro" 탭 추가
│   ├── api/
│   │   ├── political-pro/
│   │   │   └── plans/route.ts            # 신규 — POST /api/political-pro/plans
│   │   └── generate/route.ts             # 수정 — `mode === "political_pro"` 분기 추가
│   └── components/
│       ├── PoliticalPlanPicker.tsx       # 신규 — 3개 카드 비교 UI
│       └── ScriptReviewer.tsx            # 기존 — 그대로 재사용
│
├── tests/
│   ├── test_political_plan_models.py     # 신규 — 라운드트립 + 검증 규칙
│   ├── test_political_planner.py         # 신규 — Claude 응답 모킹, 3 plan 파싱, plan_to_script
│   ├── test_political_planner_prompt.py  # 신규 — 절대 준수 4항목 포함 검증
│   └── test_gemini_tts_style_prompt.py   # 신규 — style_prompt + temperature 파라미터 전달 (API 모킹)
│
├── data/
│   └── political_pro/                    # 신규 — 영상/transcript/plans/씬 클립 저장
│
└── CLAUDE.md                             # 수정 — Input Modes 표에 "political_pro" 행 추가
```

**Structure Decision**: 기존 hybrid 구조(`src/` + `app/`) 그대로 유지. 신규 모듈 8개(Python 4 + TS 2 + 테스트 4) + 수정 6개(`gemini_tts_generator.py`, `main.py`, `script_models.py` enum, `generate/route.ts`, `page.tsx`, `CLAUDE.md`). 신규 디렉토리 `data/political_pro/`만 추가.

## Complexity Tracking

### #1. TTS로 Gemini TTS 사용 (Constitution 원칙 I 글자 위배)

| 항목 | 내용 |
|------|------|
| Violation | 원칙 I이 "TTS: edge-tts MUST 사용 — 유료 TTS 금지" 명시. 본 기능은 Gemini TTS 사용. |
| Why Needed | 사용자가 명시적으로 Charon / Newscaster / Rapid / British(RP) / Temp 0.5 요구. edge-tts 한국어 음성에는 영국식 RP 아나운서 톤이 없음 → 핵심 사용자 요구 미충족. 또한 정치 콘텐츠는 임팩트 있는 뉴스 톤이 콘텐츠 정체성에 핵심. |
| Simpler Alternative Rejected Because | edge-tts `ko-KR-InJoonNeural`(angry 톤): 영국식 RP 아나운서 톤이 아니며 사용자 요구 미충족. Gemini TTS는 **무료 한도(5 RPM, 일일 한도) 안에서 변동비 $0** — 원칙 I의 진정한 의도("운영비 0") 만족. 또한 FR-019에 무료 한도 초과 시 명시적 오류로 차단하여 변동비 발생 방지. |
| Mitigation | (a) 무료 한도 모니터링, (b) FR-019 명시적 차단, (c) 향후 헌법 v1.3.0에 "원칙 I은 변동비 $0을 의미하며, 무료 API 사용 허용" 단서 추가 제안(본 plan 범위 밖). |

### #2. 정치 콘텐츠 처리 (Constitution 원칙 IV 글자 위배)

| 항목 | 내용 |
|------|------|
| Violation | 원칙 IV가 "정치/종교: 논란성 주제 → 자동 스킵" 명시. 본 기능은 정치 콘텐츠를 적극 처리. |
| Why Needed | 본 기능 자체가 정치 쇼츠 생성 도구. 사용자(개인 운영자)가 의도적으로 정치 콘텐츠 채널 운영을 시작. |
| Simpler Alternative Rejected Because | 기능 거절 시 사용자 요구 무시. "자동 스킵"의 원래 의도는 **블라인드 자동 파이프라인이 정치 글을 자동 게시하지 못하도록** 보호하는 것이지, 사용자가 의식적으로 시작한 정치 워크플로우를 금지하는 것이 아님. |
| Mitigation | (a) **사용자가 명시적으로 정치 탭 진입 + URL 입력** — 자동 트리거 없음, (b) **2단계 사용자 검수** (기획안 선택 + 스크립트 검수), (c) **자동 업로드 금지**(FR-020), (d) **결과 화면 경고**(FR-021), (e) **시스템 프롬프트에 4종 안전 가드**(FR-007: 사실만 / 의견금지 / 편향금지 / 왜곡금지). 즉 자동 파이프라인이 아니라 사용자 통제 워크플로우. |

---

## Phase 0 Output

✅ `research.md` 생성 완료 — 6개 기술 결정(Claude 단일 호출 / Gemini TTS / Constitution IV 예외 / Claude가 구간 선택 / transcript 30분 상한 / ScriptReviewer 재사용) 모두 해소.

## Phase 1 Output

✅ `data-model.md` — 6 entity (ShortsPlan, Narration, ThreePlansResult, ShortsScript 재사용, VideoClip, Transcript) + state transition + FR ↔ Entity 매트릭스
✅ `contracts/api-political-pro-plans.md` — POST /api/political-pro/plans 계약
✅ `contracts/api-generate-political-pro.md` — POST /api/generate (mode=political_pro) 계약 (Phase 1 + Phase 2)
✅ `contracts/cli-political-pro.md` — `python3 -m src.main political-pro` CLI 계약
✅ `quickstart.md` — 사전 준비 + 5분 데모(웹 / CLI) + 검증 체크리스트 + 트러블슈팅
✅ `update-agent-context.sh claude` 실행 완료 (CLAUDE.md 갱신됨)

## Post-Design Constitution Re-Check

Phase 1 산출물 검토 후 재평가:

| 원칙 | Phase 1 후 평가 | 비고 |
|------|----------------|------|
| I | ⚠️ PARTIAL (변경 없음) | Complexity Tracking #1 그대로 유효 |
| II | ✅ PASS | data-model state transition에 실패 처리 명시, contract에 모든 오류 코드 매핑 |
| III | ✅ PASS | Phase 1 산출물에 텍스트 가독성/9:16/30~60초 모두 보존 |
| IV | ⚠️ PARTIAL (변경 없음) | Complexity Tracking #2 그대로 유효, contract에 FR-020(자동 업로드 차단) 명시 |
| V | ✅ PASS | data-model.md E4: emotion_type 매핑 유지 |
| VI | ✅ PASS | data-model.md 모든 신규 entity `frozen=True` 명시, 파일 분리 계획 800줄 한도 안 |
| VII | ✅ PASS | quickstart.md에 검증 체크리스트 + 테스트 영상 자동 생성 요구 명시 |
| VIII | ✅ PASS | quickstart.md에 `pytest tests/ -v` 전체 실행 명시 |

**결정**: 재게이트 통과 — `/speckit.tasks` 진행 가능.

---

## Next Steps

| 단계 | 명령 | 비고 |
|------|------|------|
| 1. 태스크 분해 | `/speckit.tasks` | 본 plan 기반으로 의존성 순서가 정리된 작업 목록 생성 |
| 2. 구현 | `/speckit.implement` | 태스크 단위 TDD 사이클 |
| 3. 품질 점검 | `/speckit.checklist` | 추가 품질 체크 (선택) |
| 4. 사전 검증 | `python3 -m pytest tests/test_political*.py -v` + `npm run build` + 테스트 영상 1편 생성 | Constitution VII/VIII 증거 확보 |
| 5. 커밋·PR | `git commit` → `gh pr create` | Co-Authored-By: Claude 포함 |
