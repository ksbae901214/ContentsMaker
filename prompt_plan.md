# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-06-05

---

## ✅ 완료: 025 정치쇼츠 V3 — "@김정치입니다" 포맷 도입 (2026-06-05)

> 상태: **E2E 4종 레이아웃 시각 검수 PASS** — Phase 1~7 + E2E (T041/T055/T063/T071) + T082 quickstart 검증 완료. 잔존: T074 V1/V2 byte-equality baseline (V1/V2 영상 새로 생성 필요, 옵션).
> 기획 세션: 2026-06-05
> 참고 채널: [@김정치입니다](https://www.youtube.com/@김정치입니다)
> **아키텍처 모드: 완전 격리 (Total Isolation)** — 기존 파일 0 수정 원칙, 단 진입 버튼 1개 예외
>
> **검증 결과 (2026-06-05)**:
> - jpolitics 테스트: 99 passed, 3 skipped (regression baseline 미생성, SKIP OK)
> - V1/V2 회귀 테스트: **1254 passed, 1 skipped** (SC-003 297+ 한참 초과)
> - V1/V2 Remotion tsc: 0 errors (회귀 0건)
> - V3 Remotion tsc: 0 errors
> - Next.js 빌드: 47/47 페이지 컴파일 성공 (`/jpolitics` + 3 API 라우트 포함)
> - 격리 가드: 3/3 통과 (V1/V2 보호 파일 무수정 + read-only import만 + `app/page.tsx` 버튼만 추가)
> - **E2E 4종 레이아웃 (T041/T055/T063/T071)**: 모두 30.06초 영상 시각 검수 PASS
>   - talking_head: 조국 사퇴 영상 (노란 헤드라인 + 자막 + 출처 라벨 3요소)
>   - vs_card: 양향자 vs 추미애 (좌 빨강 국힘 + 우 파랑 더민주 + 인물 사진)
>   - grid_2x2: 평택을 후보 4명 (2×2 그리드 + 인물 사진 + 정당 컬러 테두리)
>   - data_card: 조국 재산 56억 (인물 사진 720×720 + 거대 빨강 "56억 원" 144px)
> - 락인 검증 (T041a): 오디오 트랙 1개 ✓ / 씬 경계 무음 검출 ✓ / clip_search_query 메타 ✓

### 요구사항
YouTube 채널 `@김정치입니다`의 영상 제작 방식을 분석하고, 그 포맷을 자동으로 재현하는 **"정치쇼츠 V3"** 탭을 신설한다. 기존 V1(`political`) / V2(`political_pro`)와 공존, 옵트인 탭.

### 🔒 격리 원칙 (사용자 lock-in)
- **모든 V3 코드는 독립 디렉토리에 격리** — `src/jpolitics/`, `src/video/remotion_v3/`, `app/jpolitics/`, `tests/jpolitics/`
- **기존 파일 편집 0** — 유일한 예외: `app/page.tsx`에 V3 진입 버튼 1개 추가 (사용자 요청)
- **기존 코드는 read-only import만** — `youtube_news_searcher`, `naver_image_search`, `_call_claude`, `gemini_backend` 등 재사용은 import만 (편집 X)
- **회귀 0 보장** — 기존 V1/V2/celebrity/briefing 297+ 테스트 자동 무회귀

### 채널 포맷 분석 결과 (샘플 3편 검증)

| 샘플 | 주제 | 레이아웃 | 데이터 패턴 |
|---|---|---|---|
| **S1** 조국 사퇴 (nPOJYSXdICI) | 1인 연설/인터뷰 | Talking Head (원본 풀스크린) + 페북 글 인서트 | 상단 노란 헤드라인 / 하단 자막 박스 / 출처 라벨 |
| **S2** 양향자 vs 추미애 (fBJH4SX02Ig) | 2인 대결/논평 | VS 카드 (좌·파랑 / 우·빨강 정당 컬러) → Talking Head | 정당 컬러 카드 + MBC 라디오 출처 |
| **S3** 평택을 후보 4명 (_eGbiXgBI6E) | 다인 비교 | 2x2 그리드 (4명 사진) + 시간별 데이터 슬라이드 | 빨강 강조 데이터 (재산/세금/공약) |

### 공통 시각 패턴 (7요소)
1. **고정 헤드라인 (Hook Title)** — 영상 전체 노란 박스 + 검정 두꺼운 한글 폰트 2줄
2. **하단 자막 박스** — 흰 라이트박스 + 실시간 캡션, 빨강 강조 가능
3. ~~채널 워터마크~~ — **본 프로젝트는 제외 (사용자 lock-in)**
4. **출처 라벨** — 하단 "출처 : XXX / YYYY.MM.DD" (외부 인용 시)
5. **레이아웃 다양화** — Talking Head / VS 카드 / 2x2 그리드 / 데이터 슬라이드
6. **정당 컬러 코드** — 민주(파랑) / 국힘(빨강) 정확 매칭
7. **데이터 강조** — 큰 빨간 숫자 (재산/세금/연도 등 비교 수치)

### 사용자 Lock-in 결정 (2026-06-05)
| 항목 | 결정 |
|------|------|
| TTS 보이스 | **V1 락인 유지 — `ko-KR-InJoonNeural` +22%** (Charon 사용 안 함) |
| 채널 워터마크 | **제외** (V3는 워터마크 없음, 출처 라벨만 유지) |
| 레이아웃 범위 | **4종 모두 구현** — `normal` / `vs_card` / `grid_2x2` / `data_card` |
| 효과음(SFX) | **영구 0** — 어떤 씬에도 효과음·BGM 삽입 금지 (FR-034, SC-011) |
| 씬 전환 효과 | **하드 컷만** — 그라데이션·페이드·디졸브 미사용 (FR-035, SC-012) |
| TTS 씬 간 gap | **300 ms 고정** — 그룹 경계에서만 0.3초 무음 (FR-036, SC-013) |
| 영상 추출 흐름 | **Gemini Files API → Claude 검색 키워드 결정 → yt-dlp 다운로드** 3단계 분업 (FR-037, SC-014) |

### V1/V2/V3 차별점

| | V1 (political) | V2 (political_pro) | **V3 (jpolitics)** |
|---|---|---|---|
| 기획 | 1단 Claude 분석 | RTF 6요소 3안 비교 | RTF + **레이아웃 자동 분류** (TH/VS/GRID/DATA) |
| 레이아웃 | 풀스크린 1종 | normal / split 2종 | **normal / vs_card / grid_2x2 / data_card 4종** |
| 자막 | 3줄 (단일색) | 1줄 4색 + emphasis | 1줄 4색 + **고정 헤드라인 노란 박스** |
| 데이터 시각화 | 없음 | 없음 | **인물 카드 + 빨강 강조 수치** |
| TTS | InJoonNeural +22% | Gemini Charon Newscaster | **InJoonNeural +22% (V1 락인 유지)** |
| 출처 라벨 | metadata만 | 하단 letterbox | 하단 letterbox **(워터마크 제외)** |
| 이미지 소스 | 원본 클립 | 원본 클립 | **원본 클립 + Naver 인물 사진 + 정당 로고 자동 페치** |

---

### 구현 단계 (완전 격리 — 10 Phase)

**Phase 1 — Spec 문서 + 샘플 보관 (read-only)**
1. `specs/010-jpolitics-v3-format/{spec,plan,tasks,data-model,research,quickstart}.md` 작성
2. `data/jpolitics_reference/` — 샘플 3편 키프레임 보관 (`/tmp/jpolitics_analysis/`에서 이동)
3. lock-in 항목: TTS=InJoonNeural+22%, 워터마크 없음, 레이아웃 4종, 진입은 메인 페이지 버튼 1개

**Phase 2 — `src/jpolitics/` 패키지 골격 + 독립 모델 (TDD)**
4. `src/jpolitics/__init__.py`, `src/jpolitics/models/__init__.py`
5. `src/jpolitics/models/script.py` — **독립 `JpoliticsScript` / `JpoliticsScene` frozen dataclass**
   - 필드: `id`, `timestamp`, `duration`, `type`, `text`, `voice_text`, `visual_layout` (`normal`/`vs_card`/`grid_2x2`/`data_card`), `subtitle_color`, `subtitle_emphasis`, `headline_pin`, `comparison_cards`, `data_emphasis_color`, `clip_path`, `clip_query`
   - Scene 상속 없음, 완전 독립 클래스
6. `src/jpolitics/models/plan.py` — 독립 `JpoliticsPlan` / `JpoliticsThreePlansResult`
7. 테스트: `tests/jpolitics/test_models.py` — 라운드트립, 카드 1~4개, 4종 layout 검증

**Phase 3 — 인물 카드 페치 모듈 (독립)**
8. `src/jpolitics/scraper/politician_card.py`:
   - `from src.scraper.naver_image_search import search_image` (read-only import)
   - `fetch_politician_card(name) -> dict` — Naver 검색 → 정면 사진 1장 → `data/politician_cards/{name}.json` 캐시
   - `PARTY_COLORS` 상수 (민주 #004EA2 / 국힘 #E61E2B / 조국혁신당 #0073CF / 개혁신당 #FF7920 / 무소속 #888)
   - `infer_party(name)` — Claude 1-shot 추론 (claude_analyzer._call_claude read-only import)
9. 테스트: 캐시 히트/미스, 무소속 회색 폴백, Naver 미발견 폴백

**Phase 4 — Planner (독립 Stage A/B)**
10. `src/jpolitics/analyzer/prompts.py` — `build_stage_a_prompt()`, `build_stage_b_prompt()`
    - Stage A: 영상 분석 + **레이아웃 분류** (`talking_head` / `vs_2way` / `comparison_grid` / `data_comparison`)
    - Stage B: 씬별 `visual_layout` + `comparison_cards` (필요시) + 첫 씬 `headline_pin` (8~14자)
11. `src/jpolitics/analyzer/planner.py`:
    - `from src.analyzer.claude_analyzer import _call_claude` (read-only import)
    - `from src.analyzer.gemini_backend import call_gemini` (read-only import)
    - `generate_three_plans(youtube_url, transcript, ...) -> JpoliticsThreePlansResult`
    - `plan_to_script(plan) -> JpoliticsScript` (카드 씬에 politician_card 페치 + 정당 컬러 주입)
12. 테스트: 4종 레이아웃 분류, 카드 페치 mock, 헤드라인 ≤14자

**Phase 5 — TTS wrapper (V1 락인 하드코딩)**
13. `src/jpolitics/tts/voice.py`:
    - `VOICE = "ko-KR-InJoonNeural"`, `RATE = "+22%"` 모듈 상수 락인
    - `synthesize(script: JpoliticsScript) -> tuple[Path, list[SceneTiming]]` — edge-tts 직접 호출
14. 테스트: 보이스 상수 변경 불가 검증, scene_timings 생성 검증

**Phase 6 — `src/video/remotion_v3/` 독립 Remotion 패키지**
15. 디렉토리 생성 + `package.json` (remotion 의존성만), `tsconfig.json`
16. `src/index.ts` → `registerRoot(Root)`
17. `Root.tsx` — V3 전용 composition 등록 (`<Composition id="JpoliticsShorts" ...>`)
18. `JpoliticsComposition.tsx` — main composition (background + PinnedHeadline + scene routing + outro + audio)
19. 컴포넌트 8종 (모두 신규):
    - `components/PinnedHeadline.tsx` — 영상 전체 상단 노란 박스 + 검정 두꺼운 폰트 2줄
    - `components/TalkingHeadScene.tsx` — 원본 클립 풀스크린
    - `components/VsCardScene.tsx` — 좌·우 분할, 정당 컬러 배경
    - `components/ComparisonGridScene.tsx` — 2x2 그리드 + 데이터 빨강 강조
    - `components/DataCardScene.tsx` — 단일 인물 카드 + 큰 데이터
    - `components/SubtitleBlock.tsx` — V2 자막 패턴 복제 (4색 + emphasis)
    - `components/Background.tsx` — V2 패턴 복제 (그라데이션)
    - `components/Outro.tsx` — V2 패턴 복제
    - `components/LetterboxFrame.tsx` — 하단 출처 라벨 영역
20. 테스트: `npx tsc --noEmit` 통과, preview 4종 스크린샷

**Phase 7 — Python renderer wrapper (독립)**
21. `src/jpolitics/video/renderer.py`:
    - `render(script: JpoliticsScript, audio_path: Path, scene_timings, output_path)` — `npx remotion render` 호출 with `src/video/remotion_v3/`
    - 자산 복사: 클립/오디오/인물 카드 → `src/video/remotion_v3/public/` (격리)
22. 테스트: subprocess mock + 자산 복사 검증

**Phase 8 — CLI entry (독립 모듈)**
23. `src/jpolitics/main.py`:
    - argparse: `python3 -m src.jpolitics.main <youtube_url>` / `--source-type topic --topic "..."`
    - 흐름: transcript → planner → 사용자 선택 (CLI prompt) → tts → renderer
24. 테스트: argparse 분기, e2e (transcript fixture)

**Phase 9 — Next.js 독립 페이지 + API (`app/jpolitics/`)**
25. `app/jpolitics/page.tsx` — V3 전용 페이지 (URL `/jpolitics`)
26. `app/jpolitics/components/JpoliticsPlanPicker.tsx`, `JpoliticsScriptReviewer.tsx`
27. `app/jpolitics/api/plans/route.ts` — V2 패턴 복제, jpolitics_main 호출
28. `app/jpolitics/api/render/route.ts` — V2 패턴 복제
29. **FR-020 업로드 차단 + FR-021 검수 필수 배너** (rose-amber)
30. 테스트: API smoke + 3줄 요약 + 해시태그

**Phase 10 — 진입 버튼 + E2E 검증 + lock-in (유일한 예외 수정)**
31. ⚠️ **유일한 기존 파일 수정**: `app/page.tsx` 헤더 영역에 V3 진입 버튼 1개 추가
    - 예: `<button onClick={() => router.push("/jpolitics")}>🟡 정치 V3</button>`
    - 기존 8개 탭 union 타입·로직·폼 모두 무수정 — 헤더 버튼만 추가
32. 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성
33. 회귀 검증: 기존 297+ 테스트 무회귀 + 신규 50+ 통과 + Next.js 빌드 + `cd remotion_v3 && npx tsc --noEmit`
34. 3줄 요약 + 해시태그 자동 첨부 검증

---

### 영향 받는 파일 (격리 모드)

**🆕 신규 파일만** (편집 0):
```
src/jpolitics/                       (Python 패키지 신규 ~12 파일)
  __init__.py, main.py
  models/{__init__,script,plan}.py
  scraper/{__init__,politician_card}.py
  analyzer/{__init__,prompts,planner}.py
  tts/{__init__,voice}.py
  video/{__init__,renderer}.py

src/video/remotion_v3/               (독립 Remotion 패키지 신규 ~12 파일)
  package.json, tsconfig.json
  src/index.ts, Root.tsx, JpoliticsComposition.tsx
  src/components/{PinnedHeadline,TalkingHeadScene,VsCardScene,
                  ComparisonGridScene,DataCardScene,SubtitleBlock,
                  Background,Outro,LetterboxFrame}.tsx

app/jpolitics/                       (Next.js 라우트 신규 ~5 파일)
  page.tsx
  components/{JpoliticsPlanPicker,JpoliticsScriptReviewer}.tsx
  api/plans/route.ts
  api/render/route.ts

tests/jpolitics/                     (격리 테스트 신규 ~6 파일)
  test_models.py, test_planner.py, test_politician_card.py,
  test_tts_voice_lockin.py, test_renderer.py, test_e2e.py

specs/010-jpolitics-v3-format/       (사양 문서 6 파일)

data/jpolitics_reference/            (샘플 키프레임)
data/politician_cards/               (인물 카드 캐시)
data/jpolitics/                      (V3 영상 출력 격리 디렉토리)
```

**🔧 기존 파일 수정** (1개만):
- `app/page.tsx` — **V3 진입 버튼 1개 추가** (헤더 영역, 기존 탭 로직 무수정)

**📖 기존 파일 read-only import** (편집 0):
- `src/scraper/youtube_news_searcher.py` — yt-dlp 검색·9:16 컷 재사용
- `src/scraper/naver_image_search.py` — Naver 이미지 검색 재사용
- `src/analyzer/claude_analyzer.py` — `_call_claude` 재사용
- `src/analyzer/gemini_backend.py` — Stage A Gemini 호출 재사용

---

### 의존성 / 사전 조건
- ✅ `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` (셀럽 모드용 이미 존재) — 인물 사진 검색에 재사용
- ✅ `MS-Hannah-NotoSans-Bold` / `Noto Sans KR Black` — 노란 헤드라인용 (Remotion 이미 설치됨)
- ✅ `data/jpolitics_reference/` — 샘플 키프레임 보관 (lock-in 확인용)
- ❌ ~~채널 워터마크 PNG~~ — **사용자 lock-in: 제외**

---

### 리스크

| 등급 | 항목 | 완화책 |
|---|---|---|
| 🔴 **HIGH** | **저작권** — 정치인 사진(Naver)·뉴스 클립 인용 = 제3자 저작물 | V2와 동일: 업로드 UI 차단(FR-020) + "검수 필수" 배너(FR-021), 보도·논평 목적 명시 |
| 🟡 **MED** | **레이아웃 오분류** — LLM이 talking_head를 grid로 잘못 분류 시 부자연 | Stage A 프롬프트에 4종 명확 예시 + 사용자 수정 가능 UI (선택 드롭다운) |
| 🟡 **MED** | **카드 데이터 환각** — Claude가 "127억" 같은 데이터를 LLM hallucination 출력 | data_card 씬은 transcript에 명시된 숫자만 인용 + 출처 라벨 강제 |
| 🟢 **LOW** | **정당 매핑 누락** — 무소속/신생 정당 헥스 컬러 미정 | `infer_party` 폴백 시 회색(#888) + 경고 로그 |
| 🟢 **LOW** | **Naver 사진 누락** — 인물명 검색 실패 | 그라데이션 폴백 + 콘솔 경고 |

---

### 비용·복잡도 (격리 모드)
- **변동비**: $0 (Naver 무료 25,000건/일, Gemini 무료 250req/일, Edge TTS 무료, Claude 기존 한도)
- **복잡도**: **HIGH (격리 모드 +5h)**
  - Phase 1 Spec: 1-2h
  - Phase 2-5 백엔드 독립 패키지: 8-10h
  - Phase 6 Remotion V3 독립 패키지 (컴포넌트 8종 + 공통 복제): 6-8h
  - Phase 7-9 Renderer + CLI + Next.js: 4-5h
  - Phase 10 진입 버튼 + E2E: 2-3h
  - TDD 테스트: 4-5h
  - **합계: 25-33h** (vs. 통합 안 18-23h, 격리 모드 +7-10h 트레이드오프)
- **신규 LOC**: ~2500 (Remotion 컴포넌트 복제분 ~1000 포함)
- **격리 가치**: 기존 297+ 테스트 자동 무회귀 + V1/V2 락인 100% 보장

---

### 검증 기준 (DoD)
- [ ] 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성 → 사용자 OK
- [ ] 고정 헤드라인 + 출처 라벨 2요소 모든 씬 노출 확인 (워터마크 제외)
- [ ] TTS = InJoonNeural +22% 하드코딩 검증 (변경 시도 시 테스트 실패)
- [ ] 단위 테스트 신규 50+ 통과 / 회귀 테스트 297+ 유지 (격리로 자동 보장)
- [ ] Next.js 빌드 success + V3 TypeScript `cd src/video/remotion_v3 && npx tsc --noEmit` 통과
- [ ] 기존 V1/V2 Remotion 빌드도 무회귀 (`cd src/video/remotion && npx tsc --noEmit`)
- [ ] 메인 페이지 V3 진입 버튼 동작 + `/jpolitics` 라우팅 확인
- [ ] 기존 V1/V2/celebrity/briefing 탭 무회귀 (탭 union 타입 무수정)
- [ ] 3줄 요약 + 해시태그 자동 첨부

---

### 참고 코드 위치 (read-only 참고용 — 편집 X)
- V2 layout split 패턴 참고: `src/analyzer/script_models.py:135-142` (필드 구조만 참조하여 JpoliticsScene 독립 작성)
- V2 SplitScreenScene 참고: `src/video/remotion/src/components/SplitScreenScene.tsx` (분할 화면 로직 참조)
- 정치_pro Stage A/B 흐름 참고: `src/analyzer/political_planner.py` (병렬 패턴 모방, import는 `_call_claude`만)
- TTS edge-tts 호출 패턴: `src/tts/edge_tts_synth.py` (구현 패턴 참조)
- Naver 이미지 검색 import: `from src.scraper.naver_image_search import search_image`
- Remotion 자산 복사 패턴: `src/video/renderer.py` (격리된 `remotion_v3/public/`로 동일 패턴 적용)
- V2 API route 구조 참고: `app/api/political-pro/plans/route.ts` (구조만 참조하여 독립 작성)
- V2 자막 분할 알고리즘: `src/editor/subtitle_split.py` (read-only import 가능, 자막 품질 동일 유지)

---

## ✅ 완료: 024 유명인 쇼츠 — 유튜브 클립 소스 추가 (2026-05-28)

> 상태: **구현 완료** (커밋: dcb20ea)
> 기획 세션: 2026-05-28 | 구현 세션: 2026-05-28

### 요구사항
유명인 쇼츠에서, 정치 topic 모드처럼 **유튜브에서 해당 인물의 실제 영상을 씬별로 검색·다운로드·9:16 컷**하여 씬 배경 영상으로 쓰는 새 옵션을 추가한다. 기존 동작(Freepik 이미지→영상 / 이미지)은 그대로 유지하고 **옵트인**으로 붙인다.

### 확정된 설계 결정 (사용자 합의)
| 항목 | 결정 |
|------|------|
| 검색어 소스 | **새 `clip_query` LLM 필드** — celebrity 프롬프트가 씬별 영상 검색어 출력("손흥민 골 장면" 등), 미출력 시 `{name} {image_query}` → `{name}` 폴백 |
| 다운로드 | **씬별 ytsearch1** — `youtube_news_searcher.build_scene_clips()` 그대로 재사용 (새 스크래핑 코드 없음) |
| 9:16 처리 | **crop·letterbox 둘 다 구현** → 동일 씬으로 샘플 2종 생성 → 사용자가 보고 lock-in (미정) |
| 기본 동작 | **새 옵션 옵트인** (`--video-source youtube`), 기본값은 현행 유지 |

### 핵심 인사이트
`src/scraper/youtube_news_searcher.py`의 검색·다운로드·컷 로직(`build_scene_clips`, `cut_scene_clip`, `search_and_download_news_clips`)이 **완전히 재사용 가능**. 새 다운로드 코드 0. 작업 본질 = "유명인 파이프라인에 클립 소스 분기 + 씬별 검색어 1필드 + UI 토글".

### 구현 단계

**Phase 1 — 데이터 모델 + 컷 모드 (TDD)**
1. `Scene`에 `clip_query: str | None = None` 추가 (`src/analyzer/script_models.py`) — `to_dict`/`from_dict` 직렬화(값 있을 때만, camelCase `clipQuery` 호환), `image_query`와 동일 패턴
2. `cut_scene_clip()`에 letterbox 모드 추가 (`src/scraper/youtube_news_searcher.py`): `crop_9x16: bool` → `crop_mode: Literal["crop","letterbox"]` (기본 `"crop"`, 하위호환). letterbox vf = `scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:color=black`. `build_scene_clips()`에 `crop_mode` 전달
3. 테스트: `clip_query` 라운드트립, `cut_scene_clip` letterbox vf 인자 생성(ffmpeg mock)

**Phase 2 — 유명인 유튜브 클립 헬퍼 (TDD)**
4. `_build_celebrity_clip_keywords(name, script)` (`src/main.py`): 씬별 검색어. 우선순위 `scene.clip_query` → `f"{name} {scene.image_query}"` → `f"{name}"`. `safe_search_keyword()`로 정리
5. `_run_celebrity_youtube_clips(name, script, *, scene_timings=None, crop_mode="crop")`: scene_durations = timing 있으면 timing 기반 else `scene.duration`. `build_scene_clips()` → `data/videos/celebrity/{ts}_{name}/`. 결과 `[{scene_id, video_path}]` 매핑(None 스킵)
6. 테스트: 검색어 빌더 폴백 체인, scene_id 매핑/None 처리(`build_scene_clips` mock)

**Phase 3 — CLI 배선**
7. `cmd_celebrity` 분기 (`src/main.py`): 새 인자 `--video-source {freepik,youtube}`(기본 freepik), `--clip-crop {crop,letterbox}`(기본 crop). `video-source=youtube`면 Step 5(TTS) 먼저 → scene_timings로 클립 컷 → render(정치_pro와 동일 순서, 싱크 정확). `metadata.source_label` 미설정 시 `"출처: YouTube"` 주입(하단 라벨 시스템 재사용)
8. 테스트: argparse 파싱 + 분기 선택

**Phase 4 — UI / API 배선**
9. celebrity 탭 토글 (`app/page.tsx`): 영상 소스 `이미지 / Freepik 영상 / 유튜브 클립` + crop 옵션
10. `app/api/generate/route.ts`: `celebrityVideoSource`/`celebrityClipCrop` → `--video-source`/`--clip-crop`
11. `app/api/celebrity-rerender/route.ts`: 동일 옵션

**Phase 5 — 샘플 검증 + lock-in**
12. 같은 인물로 crop/letterbox 샘플 2편 생성 → 비교 → 확정안 lock-in (메모리 기록)
13. 3줄 요약 + 해시태그 동반 제공 (고정 룰)

---

## ✅ 완료: 023 정치쇼츠 V2 — 주제 입력 모드 추가 (2026-05-26)

(상세는 prompt_plan.md.bak3 참조)

---

## 이전 계획

(이전 prompt_plan.md는 prompt_plan.md.bak3에 보관)
