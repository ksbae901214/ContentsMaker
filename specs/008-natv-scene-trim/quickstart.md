# Quickstart: TRIM-01

**Feature**: NATV 씬 구간 드래그 트리밍
**Date**: 2026-04-20

## 사전 준비

```bash
# 1. Python venv + 의존성
pip install -r requirements.txt

# 2. Node 의존성 (root + Remotion 별도)
npm install
cd src/video/remotion && npm install && cd -

# 3. ffmpeg / ffprobe 설치 확인
ffmpeg -version
ffprobe -version

# 4. Next.js dev server
npm run dev   # → http://localhost:3000
```

## E2E 시나리오 (Phase 5 완료 시 검증)

### 1단계 — NATV 영상 생성

1. `http://localhost:3000` 접속
2. **📺 NATV 클립** 탭 선택
3. YouTube URL 입력: `https://www.youtube.com/watch?v=AU5Ymu6--Ao`
4. 톤 = "분노", TTS 끄기, BGM 끄기 (기본값 그대로 가능)
5. **📺 NATV 클립 쇼츠 생성** 클릭
6. 약 2~3분 대기 → 씬 3~8개로 초기 렌더 완료

### 2단계 — 씬 구간 편집

1. 결과 화면에서 임의 씬 카드 우측 하단 **🎬 구간 편집** 버튼 클릭 (Phase 5 산출물)
2. 패널이 펼쳐지면 하단에 프로그레스바 + 핸들 두 개가 나타남
3. 핸들을 **드래그** 하거나 키보드 **←/→** 로 조정
4. **자동 맞춤** 버튼으로 TTS 길이에 맞출 수 있음
5. **저장** 클릭 → 상단에 "변경 있음" 배지 점등

### 3단계 — 최종 렌더링

1. 우상단 **최종 렌더링** 버튼 클릭
2. 2~3분 대기 → 하단 MP4 미리보기 표시
3. 트리밍한 구간이 정확히 반영됐는지 육안 확인

## 예상 파일 변화

| 파일 | 상태 |
|---|---|
| `data/scripts/<ts>_<title>.json` | 씬별 `source_video/source_start/source_end` 필드 업데이트 |
| `data/natv_clips/AU5Ymu6--Ao.mp4` | **변동 없음** (원본 보존) |
| `data/natv_clips/scene_<ts>_NN.mp4` | 초기 프리뷰용, 최종 렌더는 사용 안 함 |
| `data/outputs/<ts>_<title>.mp4` | 새 렌더 결과 |

## 검증 체크리스트

- [ ] 트리밍 전/후 스크립트 JSON diff 에서 해당 씬의 `source_start/end` 만 변경
- [ ] 최종 MP4 에서 트리밍한 구간만 보임 (화면 속 원본 발언자 입 모양과 TTS 일치)
- [ ] 다른 탭(image, manual) 으로 생성한 결과에는 **구간 편집** 버튼 표시 **안 됨**
- [ ] pytest 전체 통과 (859 ≥)
- [ ] `npx tsc --noEmit` 0 errors

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 슬라이더 움직여도 프리뷰 안 움직임 | `<video>` 의 `currentTime` 시크 실패 | 브라우저 캐시 비우고 재시도 |
| 저장 버튼 404 | `/api/scene/trim` 미배포 | dev 서버 재기동 |
| "403 NATV 씬이 아님" | 해당 씬 `source_video=null` | NATV 모드로 재생성 필요 |
| 최종 MP4 에 트리밍 반영 안 됨 | `scene_videos` 경로 우선 | Phase 2 완료 이후 버전인지 확인 |

## Hand-off 다음

- Phase 1 시작 → `/auto` 또는 `/tdd`
- Phase 단위 태스크 분해 → `/speckit.tasks`
