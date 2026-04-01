# Research: 영상 제작/편집 기능 고도화

## 1. Seedance 2.0 API 통합

**Decision**: Seedance 2.0을 기본 AI 영상 생성 도구로 사용

**Rationale**:
- 비용 효율 최고: 720p 5초 ~$0.05, 1080p ~$0.25
- 9:16 종횡비 네이티브 지원 (Shorts 최적)
- Image-to-Video 지원 (GPT Image 연계)
- Text-to-Video 지원
- 비동기 API (생성 요청 → 상태 확인 → 다운로드)

**Alternatives considered**:
- Sora 2 (OpenAI): 최고 품질이지만 10-50배 비쌈 ($0.50/5초 720p). 프리미엄 옵션으로 추후 추가 가능
- Runway Gen-3: 유사 가격대이나 9:16 지원이 제한적

**API 구조**:
- POST /generate → task_id 반환
- GET /task/{task_id} → 상태 확인 (pending/processing/completed/failed)
- GET /task/{task_id}/download → 영상 다운로드
- 생성 시간: 720p 5초 기준 1-3분, 1080p 3-5분

## 2. 드래그앤드롭 라이브러리

**Decision**: @dnd-kit/core 사용

**Rationale**:
- React 19 호환
- 접근성 지원 내장
- 커스텀 센서 및 충돌 감지 알고리즘
- 정렬 가능 리스트(SortableContext) 내장
- 번들 크기 작음

**Alternatives considered**:
- react-dnd: 오래된 API, React 19 호환 불확실
- react-beautiful-dnd: Atlassian이 유지보수 중단
- 직접 구현: 접근성/터치 지원 등 복잡도 높음

## 3. Remotion Player (실시간 미리보기)

**Decision**: @remotion/player 패키지 사용

**Rationale**:
- Remotion 에코시스템 내장 컴포넌트
- 동일한 React 컴포지션을 브라우저에서 바로 재생
- props 변경 시 즉시 반영 (리렌더링 불필요)
- 스크러빙, 시크, 일시정지 내장

**제한사항**:
- 최종 렌더링(MP4)과 100% 동일하지 않을 수 있음 (폰트 렌더링, 비디오 코덱 차이)
- 무거운 컴포지션은 브라우저에서 느릴 수 있음

## 4. 자막 스타일링

**Decision**: Scene 모델에 SubtitleStyle 필드 추가, Remotion에서 동적 스타일 적용

**Rationale**:
- 프리셋 기반 빠른 적용 + 상세 커스터마이즈 모두 지원
- JSON으로 직렬화하여 프로젝트 저장/로드 가능
- Remotion의 CSS-in-JS 스타일링과 자연스럽게 통합

**프리셋 정의**:
- 뉴스형: 하단 20%, 검정 배경 70% 투명도, 흰색 텍스트, Noto Sans KR Bold
- 유머형: 중앙, 배경 없음, 노란색 텍스트, 큰 크기(72px), 그림자 강하게
- 감성형: 하단 30%, 반투명 그라데이션 배경, 흰색 텍스트, 이탤릭

## 5. 트랜지션 효과

**Decision**: Remotion의 interpolate + spring 조합으로 5종 트랜지션 구현

**효과 목록**:
1. **Fade**: opacity 0→1 (기본값, 현재 구현)
2. **Slide Left**: translateX 100%→0
3. **Slide Up**: translateY 100%→0
4. **Zoom In**: scale 1.5→1 + opacity 0→1
5. **Dissolve**: 이전 씬 fadeOut + 현재 씬 fadeIn 동시
6. **Wipe**: clip-path 기반 수평 와이프

## 6. 효과음 소스

**Decision**: Pixabay Sound Effects에서 로열티프리 효과음 수동 다운로드

**카테고리 및 수량**:
- 놀람 (3개): 띠링, 두둥, 어!?
- 웃음 (3개): 크크크, 하하하, 빵터짐
- 감동 (2개): 잔잔한 종소리, 훈훈한 효과음
- 강조 (3개): 두구두구, 짜잔, 타다
- UI (2개): 전환 효과음, 클릭

**포맷**: MP3, 1-3초, 44.1kHz

## 7. 번역 API

**Decision**: 기존 OpenAI GPT API 활용 (별도 번역 API 불필요)

**Rationale**:
- 이미 OPENAI_API_KEY 설정되어 있음
- GPT-4o-mini로 비용 최소화
- 문맥 기반 번역으로 자막 특성에 맞는 번역 가능
- 영어/일본어 두 언어만 지원하면 충분

**비용**: GPT-4o-mini 기준 영상 1개당 ~$0.001 (매우 저렴)
