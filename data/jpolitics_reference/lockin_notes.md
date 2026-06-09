# 정치쇼츠 V3 (@김정치입니다 포맷) — 사용자 Lock-in 기록

**최종 결정 날짜**: 2026-06-05
**Spec**: `specs/010-jpolitics-v3-isolated/spec.md`
**상태**: Phase 1~7 구현 완료, E2E (T041/T055/T063/T071) 잔존

## 🔒 변경 금지 lock-in

### 1. TTS 락인
- **보이스**: `ko-KR-InJoonNeural`
- **속도**: `+22%`
- **씬 간 무음**: `300ms ± 30ms` (그룹 경계에서만 — FR-036/SC-013)
- 구현 파일: `src/jpolitics/tts/voice.py` — 상수 하드코딩 + 함수 시그니처에 voice/rate/gap 파라미터 부재 (락인 가드 테스트로 보호)

### 2. 워터마크 제외
- V3 영상에는 외부 워터마크 미부착
- 자동 업로드 영구 차단 (FR-029)
- 검수 필수 배너 강제 (FR-030)

### 3. 4종 레이아웃 (감정 4종 대신)
- `talking_head` — 1인 인터뷰/연설 (US1)
- `vs_2way` / `vs_card` — 두 인물 좌·우 분할 (US2)
- `comparison_grid` / `grid_2x2` — 3~4인 비교 (US3)
- `data_comparison` / `data_card` — 1인 + 큰 데이터 강조 (US4)
- Constitution V 원칙(Emotion-Driven) 정당화 기록: 정치 콘텐츠 차별점 = 시각 구조

### 4. 효과음 + BGM 영구 0
- 오디오 트랙은 TTS 1개만 (FR-034/SC-011)
- `JpoliticsAudioConfig.sfx_enabled == False`, `bgm_enabled == False`
- 모든 씬 `sfx_trigger == None`

### 5. 씬 전환 효과 영구 0
- 하드 컷만 (FR-035/SC-012)
- 그라데이션·페이드·디졸브 미사용
- 모든 씬 `transition_effect == "none"`
- Remotion `<Sequence>` 직접 연결, opacity interpolation 없음

### 6. 영상 추출 흐름 3단계 분업 (FR-037/SC-014)
1. **Gemini Files API** — YouTube URL 멀티모달 분석 → `transcript + key_moments[]`
2. **Claude Stage A/B** — 레이아웃 4종 분류 + 3 angle plans + 씬별 `clip_search_query` + `clip_source_timestamp`
3. **yt-dlp** — 9:16 letterbox cut → `clip_path`

### 7. 진입 버튼 1개만 추가 (격리 모드 예외)
- 유일한 기존 파일 수정: `app/page.tsx`
- 헤더에 `🟡 정치 V3` 버튼 추가 → `/jpolitics` 라우트
- 8개 탭 union 타입·로직·폼 **무수정** 유지

## 📂 격리 디렉토리 트리

```
src/jpolitics/                 # 신규 독립 Python 패키지
src/video/remotion_v3/         # 신규 독립 Remotion 패키지
app/jpolitics/                 # 신규 Next.js 라우트
tests/jpolitics/               # 격리 테스트 디렉토리
data/jpolitics/                # V3 출력 (격리)
data/politician_cards/         # 인물 카드 캐시
data/jpolitics_reference/      # 채널 샘플 키프레임 (본 디렉토리)
```

## 🧪 검증 결과 (2026-06-05)

| 항목 | 결과 | 기준 |
|---|---|---|
| jpolitics 테스트 (US1+US2+US3+US4) | 99 passed, 3 skipped | 모든 단위·통합 통과 |
| V1/V2 회귀 테스트 | 1254 passed, 1 skipped | SC-003 297+ 초과 |
| V1/V2 Remotion tsc | 0 errors | 회귀 0건 |
| V3 Remotion tsc | 0 errors | TypeScript 무오류 |
| Next.js 빌드 | 47/47 success | 정적·동적 모두 컴파일 |
| 격리 boundary 가드 | 3/3 pass | SC-010 / FR-026 |

## 📄 샘플 자료

- `sample1.mp4`, `sample2.mp4`, `sample3.mp4` — 채널 샘플 영상 3편
- `frame_*.png` — 키프레임 추출
- `s2_*.png`, `s3_*.png` — 시청 검증 캡처

## 🚧 잔존 작업

- **E2E 시각 검수 (사용자 수동)**:
  - T041 — `python3 -m src.jpolitics.main <YouTube URL> --select-plan 1` → talking_head 60초
  - T055 — VS 카드 (양향자 vs 추미애 등 토픽 모드)
  - T063 — 2×2 그리드 (평택을 후보 4명 비교)
  - T071 — 데이터 카드 (조국 재산 56억)
  - T041a — 락인 검증 ffprobe (TTS gap 300ms, 오디오 트랙 1개, 하드 컷)

## 🔗 관련 문서

- Spec: `specs/010-jpolitics-v3-isolated/spec.md`
- Plan: `specs/010-jpolitics-v3-isolated/plan.md`
- Tasks: `specs/010-jpolitics-v3-isolated/tasks.md`
- Quickstart: `specs/010-jpolitics-v3-isolated/quickstart.md`
