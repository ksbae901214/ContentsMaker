# Phase 0 Research — 정치쇼츠 V3 격리 모드

**Date**: 2026-06-05
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## R1. LLM 레이아웃 자동 분류 패턴

**Decision**: Gemini 2.5 Flash Stage A에서 영상 분석과 동시에 레이아웃 분류 (`talking_head` / `vs_2way` / `comparison_grid` / `data_comparison`) 1-shot 추가.

**Rationale**:
- V2가 이미 Gemini Stage A로 영상 분석 + 3개 angle 분류를 수행 중이므로, 동일 호출에 분류 출력 1필드만 추가하면 비용 0 증가.
- Gemini의 멀티모달 능력으로 영상 시각 구조 직접 분석 가능 (자막만 보고 추측하지 않음).
- 사용자가 검수 화면(FR-014)에서 4종 드롭다운으로 수동 변경 가능 → LLM 오분류 위험 완화.

**Alternatives considered**:
1. **Claude Stage B에서 분류**: 자막 기반 분류는 시각 구조를 못 봐 정확도 낮음. 거부.
2. **사용자 수동 선택**: 자동화 가치 0. 거부.
3. **별도 분류 LLM 호출**: 비용 1회 추가, 격리 모드 원칙 위배. 거부.

**Prompt 예시 (요약)**:
```
영상 transcript 분석 후, 핵심 시각 구조를 다음 4종 중 하나로 분류하라:
- talking_head: 1인 인터뷰/연설/논평
- vs_2way: 2인 대결/대립 (예: A vs B)
- comparison_grid: 3~4인 비교 (선거구 후보 비교)
- data_comparison: 단일 인물의 데이터 강조 (재산/세금)
```

## R2. 인물 카드 이미지 페치 — Naver vs 대안

**Decision**: Naver 이미지 검색 API (셀럽 모드와 동일 인프라) + `data/politician_cards/{name}.json` 로컬 캐시.

**Rationale**:
- 셀럽 모드(`src/scraper/naver_image_search.py`)에서 25,000 req/일 무료 한도 검증 완료.
- 한국 정치인 검색 결과 품질이 Google/Bing보다 우수 (국내 포털 특성).
- 이미 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 환경변수 설정됨 → 추가 설정 0.
- 캐시로 동일 인물 재검색 시 200ms 이하 응답 (SC-005).

**Alternatives considered**:
1. **Wikipedia API**: 정면 단독 사진 매칭률 낮음. 거부.
2. **Freepik 이미지 생성**: 변동비 발생 + 실제 인물 아닌 일러스트로 변형 위험. 거부.
3. **DALL-E / Imagen 생성**: 실제 정치인 외형 재현 불확실 + 변동비. 거부.

**캐시 스키마**:
```json
{
  "name": "양향자",
  "party": "국민의힘",
  "party_color": "#E61E2B",
  "photo_path": "data/politician_cards/photos/양향자.jpg",
  "fetched_at": "2026-06-05T10:00:00",
  "search_query": "양향자 의원"
}
```

## R3. 정당명 → 헥스 컬러 매핑 소스

**Decision**: `src/jpolitics/scraper/politician_card.py` 모듈 상수 `PARTY_COLORS` 사전 정의 + 미매핑 정당 회색(#888) 폴백.

**Rationale**:
- 한국 주요 정당 5~10개 정도이므로 정적 매핑이 가장 단순·정확.
- 정당 컬러는 공식 로고에서 추출 (위키피디아 인포박스 또는 공식 사이트).
- 신생/무소속은 회색 폴백 + 경고 로그로 안전하게 처리 (FR-028).

**확정 매핑 (Phase 1 기준)**:
```python
PARTY_COLORS = {
    "더불어민주당": "#004EA2",   # 공식 청색
    "국민의힘":     "#E61E2B",   # 공식 적색
    "조국혁신당":   "#0073CF",   # 공식 청색
    "개혁신당":     "#FF7920",   # 공식 주황
    "정의당":       "#F9DD24",   # 노랑
    "진보당":       "#D6001C",   # 적색
    "기본소득당":   "#00B05E",   # 녹색
    "무소속":       "#888888",
    "기타":         "#888888",
}
```

**Alternatives considered**:
1. **LLM 추론으로 컬러 매번 생성**: 일관성 깨짐 + 비용. 거부.
2. **사용자 입력**: UX 저하. 거부.
3. **위키피디아 스크래핑**: 격리 모드 위배 + 응답 시간. 거부.

## R4. TTS 락인 가드 — V1 InJoonNeural +22% 보장

**Decision**: `src/jpolitics/tts/voice.py`에 모듈 상수 `VOICE = "ko-KR-InJoonNeural"`, `RATE = "+22%"` 하드코딩 + 환경변수/인자로 변경 불가 + 테스트 어설션.

**Rationale**:
- 사용자 메모리 [[feedback_political_shorts_lockin]] 명시: "박근혜·추김토론 영상에서 검증된 InJoonNeural+22%".
- V2가 Gemini Charon Newscaster로 분기를 만들었으나 V3는 V1 락인을 명시 lock-in.
- 테스트 `test_tts_voice_lockin.py`에서 보이스/속도 변경 시도 시 즉시 실패 (SC-008).

**가드 코드 패턴**:
```python
# src/jpolitics/tts/voice.py
VOICE: Final[str] = "ko-KR-InJoonNeural"
RATE: Final[str] = "+22%"

def synthesize(script, output_path):
    # VOICE/RATE는 인자로 받지 않음 — 함수 시그니처에 보이스 변경 진입점 없음
    return await edge_tts_synthesize(text, voice=VOICE, rate=RATE, ...)
```

**Alternatives considered**:
1. **환경변수로 보이스 토글**: 락인 깨질 위험. 거부.
2. **함수 인자로 보이스 받기**: 호출자가 임의 변경 가능. 거부.

## R5. Remotion V3 독립 패키지 구조

**Decision**: `src/video/remotion_v3/`에 별도 `package.json` + `tsconfig.json` + `node_modules/` 분리. 자체 `npm install` 필요. 기존 `src/video/remotion/`과 완전 독립.

**Rationale**:
- Remotion CLI는 프로젝트 디렉토리 기준으로 동작 (`npx remotion render <entry>` + cwd 인식).
- 두 패키지가 같은 `node_modules`를 공유하면 의존성 충돌 시 V1/V2 영상 깨질 위험.
- 디스크 비용 +200MB 정도이나 격리 가치가 더 큼.

**package.json (V3)** 최소 의존성:
```json
{
  "name": "jpolitics-remotion-v3",
  "private": true,
  "dependencies": {
    "remotion": "^4.0.0",
    "@remotion/cli": "^4.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}
```

**Alternatives considered**:
1. **`src/video/remotion/`에 V3 Composition만 추가**: 기존 파일 수정 필요 (Root.tsx). 격리 원칙 위배. 거부.
2. **npm workspaces로 공유**: 의존성 충돌 위험 + 격리 가치 감소. 거부.
3. **Remotion Lambda 사용**: 변동비 발생 (원칙 I 위배). 거부.

## R6. 격리 모드에서 자막 분할 알고리즘 재사용

**Decision**: `src/editor/subtitle_split.py`를 **read-only import**하여 그대로 사용. V3 자막 품질 자동으로 V2와 동일 수준 유지.

**Rationale**:
- V2가 검증한 분할·줄바꿈 알고리즘은 한국어 조사·종결어미 처리 등 비용이 컸음 (Feature 018-019).
- import는 편집이 아니므로 격리 원칙 무위배.
- V2 알고리즘 개선 시 V3도 자동 혜택.

**Alternatives considered**:
1. **V3에 자막 알고리즘 복제**: 코드 중복 + 동기화 부담. 거부.
2. **V3 전용 단순 분할**: 자막 품질 저하 (User Story 1 acceptance 위배). 거부.

## R7. Renderer 자산 격리 — public/ 디렉토리 충돌 방지

**Decision**: V3 렌더러는 `src/video/remotion_v3/public/`을 자산 디렉토리로 사용 (기존 `public/`과 분리).

**Rationale**:
- 기존 V1/V2 렌더러가 루트 `public/` 또는 `src/video/remotion/public/`을 사용 중.
- V3 자산을 동일 디렉토리에 복사하면 파일명 충돌 가능 (씬 클립 등).
- 격리 디렉토리 사용으로 V1/V2 영상 생성 중에도 V3 영상 동시 생성 가능 (Edge Case 처리).

**렌더 명령**:
```bash
cd src/video/remotion_v3 && \
  npx remotion render src/index.ts JpoliticsShorts {output} \
  --props='{...}'
```

**Alternatives considered**:
1. **루트 `public/` 공유**: 동시 실행 시 파일명 충돌. 거부.
2. **임시 디렉토리 매 렌더 생성**: 디스크 I/O 증가, 캐시 효율 저하. 거부.

## R8. Next.js 라우트 파일 기반 자동 등록

**Decision**: `app/jpolitics/page.tsx` + `app/jpolitics/api/*/route.ts`를 추가하면 Next.js 16의 파일 기반 라우터가 자동으로 `/jpolitics`, `/api/jpolitics/*` 경로 매핑.

**Rationale**:
- Next.js 16의 App Router는 별도 라우터 설정 파일 없이 디렉토리 구조 = URL 구조.
- 기존 `app/page.tsx`나 `app/layout.tsx` 수정 불필요.
- 진입 버튼 1개만 `app/page.tsx`에 추가 (사용자 명시 예외).

**Alternatives considered**:
1. **Pages Router 사용**: 프로젝트가 App Router 표준. 거부.
2. **Modal로 V3 띄우기**: 메인 페이지 수정 필요. 거부.

## R9. 진입 버튼 위치 — 헤더 vs 탭 행

**Decision**: `app/page.tsx` 헤더 영역에 amber 색상 배지 버튼 1개 추가 (`🟡 정치 V3`).

**Rationale**:
- 헤더는 모든 탭에서 공통 노출 → 어느 탭에 있든 V3 진입 가능.
- amber 색상으로 V1(파랑) / V2(rose) / V3(amber) 시각 구분.
- `next/navigation`의 `useRouter().push("/jpolitics")` 1줄 핸들러.

**구현 패턴**:
```tsx
// app/page.tsx 헤더 영역 (유일한 수정)
<button
  onClick={() => router.push("/jpolitics")}
  className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg text-sm font-bold"
>
  🟡 정치 V3
</button>
```

**Alternatives considered**:
1. **탭 행에 9번째 탭으로 추가**: tab union 타입·로직 수정 필요. 격리 위배. 거부.
2. **별도 메뉴 페이지 신설**: 추가 클릭 1회 필요, UX 저하. 거부.

## R10. 영상 출력 디렉토리 격리 — `data/jpolitics/`

**Decision**: `data/jpolitics/{ts}_{slug}/{video.mp4, plans.json, script.json, summary.txt}` 구조로 모든 V3 산출물 격리.

**Rationale**:
- V1(`data/outputs/`) / V2(`data/political_pro/`) 와 분리하여 충돌 방지.
- 동일 timestamp slug로 영상·기획안·스크립트·요약을 그룹화하여 검수·재실행 용이.
- FR-004 요구사항 충족.

**디렉토리 예시**:
```
data/jpolitics/
└── 20260605_104530_조국_사퇴/
    ├── plans.json
    ├── script.json
    ├── video.mp4
    ├── audio.mp3
    ├── transcript.json
    └── summary.txt   # 3줄 요약 + 해시태그
```

## R11. 회귀 보장 패턴 — V1/V2 영상 바이트 일치 (SC-010)

**Decision**: CI에 V1/V2 fixture 입력으로 렌더 → V3 도입 전후 영상 MD5 해시 비교 테스트 추가 (`tests/test_v1_v2_regression.py`).

**Rationale**:
- 격리로 인해 자동 보장되나, 명시 가드로 회귀 즉시 감지.
- Remotion 영상은 결정론적 (deterministic seed) → 동일 입력 → 동일 바이트.
- 첫 실행에서 fixture MD5 저장, 이후 비교.

**테스트 예시**:
```python
def test_v1_video_bytes_unchanged_after_v3():
    fixture = "tests/fixtures/v1_baseline.json"
    output = run_v1_render(fixture)
    expected_md5 = "abc123..."  # 첫 실행 후 저장
    assert hashlib.md5(output.read_bytes()).hexdigest() == expected_md5
```

**Alternatives considered**:
1. **시각 비교**: 비용 큼 + 미세 픽셀 차이로 false negative. 거부.
2. **테스트 생략**: SC-010 검증 불가. 거부.

---

## R12. 효과음(SFX) 영구 제거 (FR-034)

**Decision**: V3 영상에 효과음/SFX/BGM을 모두 제외. 오디오 트랙은 TTS 합성 결과 1개만.

**Rationale**:
- 채널 @김정치입니다 분석 3편 모두 효과음·BGM 사용 안 함 (TTS만 사용).
- 정치 콘텐츠는 발언·자막 전달력이 핵심 → 효과음은 산만함을 유발.
- 데이터 모델 락인: `JpoliticsScene.sfx_trigger = Literal[None]` (필드 자체가 가드).
- Remotion 락인: `<Audio>` 컴포넌트는 TTS 1개만 등장.

**Alternatives considered**:
1. **씬별 옵션 sfx_path**: 사용자 임의 추가 가능성 = 락인 위배. 거부.
2. **BGM 자동 매칭**: V1/V2 BGM 시스템과 격리 원칙 위배. 거부.

## R13. 씬 전환 효과 제거 — 하드 컷 락인 (FR-035)

**Decision**: 씬과 씬 사이 전환에 그라데이션/페이드/디졸브/슬라이드를 미사용. 직접 컷.

**Rationale**:
- 채널 @김정치입니다 3편 모두 하드 컷 전환만 사용.
- 30~60초 짧은 영상에서 전환 효과는 인지 부담만 증가시킴.
- 데이터 모델 락인: `JpoliticsScene.transition_effect = Literal["none"]`.
- Remotion 락인: `<Sequence>` 직접 연결, opacity interpolation 미사용.

**Alternatives considered**:
1. **씬별 transition 선택**: 락인 위배. 거부.
2. **첫 씬 fade-in**: 인지적으로 자연스러우나 채널 패턴 위배. 거부.

## R14. TTS 씬 간 무음 gap 0.3초 고정 (FR-036)

**Decision**: 씬 합성 시 그룹 경계에서 정확히 300 ms 무음 삽입. 그룹 내부 분할 자막(`subtitle_group_id` 동일)은 0초 연속.

**Rationale**:
- 사용자 lock-in 명시 값.
- 0초 (V2 일부 패턴): 너무 빠름, 자막 인지 부족.
- 1초 (긴 호흡): 답답함, 시청 유지율 저하.
- 0.3초: 자연 호흡 + 자막 인지 가능한 균형점.
- V2 패턴 `src/editor/subtitle_split.py`의 `subtitle_group_id` 재사용해 그룹 경계 식별.

**구현 패턴**:
```python
# src/jpolitics/tts/voice.py
INTER_SCENE_GAP_MS: Final[int] = 300

async def synthesize(script, output_path):
    audio_parts = []
    for i, scene in enumerate(script.scenes):
        part = await edge_tts_synthesize(scene.voice_text, voice=VOICE, rate=RATE)
        audio_parts.append(part)
        # 그룹 경계에서만 gap 삽입
        if i < len(script.scenes) - 1 and not _same_group(scene, script.scenes[i+1]):
            audio_parts.append(silence(INTER_SCENE_GAP_MS))
    return concatenate(audio_parts), scene_timings
```

**Alternatives considered**:
1. **씬마다 무조건 gap**: 분할 자막 그룹 내부에도 gap → 어색. 거부.
2. **사용자 설정 가능**: 락인 위배. 거부.

## R15. 영상 추출 흐름 — Gemini 분석 → Claude 검색 키워드 → yt-dlp 다운로드 (FR-037)

**Decision**: 3단계 분업 파이프라인:
1. **Gemini Files API**: YouTube URL 업로드 → 멀티모달 분석 → `transcript + key_moments[{start, end, summary}]`
2. **Claude (Stage B)**: Gemini 결과 입력 → 씬별 `clip_search_query` 결정 + `clip_source_timestamp` (원본 영상에서 사용할 구간)
3. **yt-dlp** (read-only import `src/scraper/youtube_news_searcher.py`): Claude 결정 키워드로 `ytsearch1` 검색 + 다운로드 + ffmpeg 9:16 letterbox cut

**Rationale**:
- Gemini의 멀티모달 분석 강점 (영상+자막 동시) + Claude의 추론·검색 키워드 결정 강점을 분업.
- 단일 LLM 사용 대비: Gemini만 사용 시 추론 약함, Claude만 사용 시 영상 분석 약함.
- 비용: Gemini Files API 무료 한도 + Claude 기존 한도 → $0.
- 격리: 새 스크래핑 코드 0 (V2의 `build_scene_clips`, `cut_scene_clip` read-only 재사용).

**클립 사용 매핑**:
- `visual_layout = "talking_head"` → 원본 영상의 `clip_source_timestamp` 구간 cut 후 풀스크린
- `visual_layout = "vs_card"` → 보조 검색 (정치인별 추가 클립) + 인물 카드 사진
- `visual_layout = "grid_2x2"` → 인물 카드 사진만 (보조 클립 없음, 그리드 영상이 메인)
- `visual_layout = "data_card"` → 인물 카드 사진만

**Alternatives considered**:
1. **Claude만 사용 + yt-dlp transcript 추출**: 영상 분석 약함, key_moments timestamp 부정확. 거부.
2. **Gemini가 모든 검색 키워드 결정**: 추론 깊이 부족, 정확도 낮음. 거부.
3. **사용자 수동 키워드 입력**: 자동화 가치 0. 거부.

## 미해결 NEEDS CLARIFICATION

**없음** — 사용자 lock-in 7건 (TTS InJoonNeural / 워터마크 제외 / 4종 레이아웃 + 진입 버튼 1개 + **효과음 0 + 전환 효과 0 + TTS gap 0.3s + Gemini→Claude→yt-dlp 흐름**)으로 모든 결정 명확.

## 다음 단계 → Phase 1

- [data-model.md](./data-model.md) — JpoliticsScript / JpoliticsScene / PoliticianCard / JpoliticsPlan / JpoliticsThreePlansResult 5종 엔티티
- [contracts/](./contracts/) — CLI / API / Remotion props 스키마
- [quickstart.md](./quickstart.md) — 개발자 가이드
