# Research: 006-video-shorts-mode

**Date**: 2026-04-02

## R-001: 주제 입력 모델 설계 방식

**Decision**: 기존 `BlindPost` 모델과 병렬로 `TopicInput` frozen dataclass를 신규 생성한다. 공통 분석 파이프라인은 유지하되, 프롬프트 빌더만 분기한다.

**Rationale**: BlindPost는 title/author/body/comments 구조로 블라인드 게시글 특화. TopicInput은 topic/style/tone/details로 구조가 다르다. 공통 상위 클래스를 만들면 두 모델 모두 불필요한 필드를 갖게 되어 복잡도만 증가. 별도 모델 + 분석 함수 분기가 깔끔하다.

**Alternatives considered**:
- BlindPost 확장 (mode 필드 추가): 기존 모델 오염, 역호환 리스크
- Union 타입 사용: 런타임 타입 체크 복잡

## R-002: 이미지 스타일 프리셋 구현 방식

**Decision**: `prompt_builder.py`에 `IMAGE_STYLE_PRESETS` 딕셔너리 추가. `build_image_prompts(script, image_style="webtoon")` 파라미터로 스타일 전달. 웹툰 외 스타일은 레퍼런스 이미지를 사용하지 않는다.

**Rationale**: 현재 `STYLE_PREFIX`는 한국 웹툰 하드코딩. 스타일 프리셋 딕셔너리로 교체하면 기존 동작(webtoon 기본값) 유지하면서 확장 가능. 3D Pixar/실사풍/애니메는 레퍼런스 이미지가 의미 없으므로(스타일이 완전히 다름) `images.generate()` 직접 사용이 적합.

**Alternatives considered**:
- 스타일별 별도 함수: 코드 중복 심함
- 설정 파일(YAML): 오버엔지니어링, 현재 4종으로 충분

## R-003: Seedance API 통합 패턴

**Decision**: 기존 `src/video_gen/` 스켈레톤(base.py, seedance_gen.py, factory.py)을 구현 완성한다. `generate_and_wait()` 편의 함수 추가 (generate → poll → download 통합). httpx 비동기 클라이언트 사용.

**Rationale**: 스켈레톤이 이미 존재하며 `VideoGeneratorBase` ABC, `VideoResult`, `VideoStatus` dataclass가 정의됨. 인터페이스 변경 없이 TODO 구현만 채우면 됨. httpx는 async 지원 + 타임아웃 관리가 우수.

**Alternatives considered**:
- aiohttp: 의존성 크기 큼, httpx가 더 현대적
- requests (동기): TTS와 병렬 실행 불가

## R-004: 파이프라인 분기 설계

**Decision**: `route.ts`에서 `mode`(blind/topic)와 `visualMode`(manga/video), `imageStyle` 3개 파라미터로 분기. 분석 단계에서 mode별 함수 호출, 비주얼 단계에서 visualMode별 분기.

**Rationale**: 
- mode: 입력 소스 결정 (BlindPost vs TopicInput)
- visualMode: 비주얼 생성 방식 결정 (GPT Image vs Seedance)
- imageStyle: 이미지 스타일 결정 (manga 모드에서만 유효)
- 이 3축 분리로 모든 조합(blind+manga+webtoon, topic+video, topic+manga+3d_pixar 등) 커버.

**Alternatives considered**:
- 단일 mode 파라미터: 조합 폭발 (blind-manga-webtoon, blind-video, topic-manga-3d, ...)
- 프론트엔드에서 전부 결정: 백엔드 검증 누락 위험

## R-005: 분석 프롬프트 분기 전략

**Decision**: `TOPIC_ANALYZE_PROMPT` 신규 템플릿 + `build_topic_prompt()` 함수 추가. 기존 `ANALYZE_PROMPT`는 변경하지 않는다. visual_mode="video"일 때 Rule 12(motion_prompt 생성) 포함.

**Rationale**: 블라인드 프롬프트의 11개 규칙 중 일부(PII 마스킹, 댓글 처리 등)는 주제 입력에 불필요. 프롬프트를 분리하면 각 입력 유형에 최적화된 규칙 세트 유지 가능. 공통 규칙(감정 감지, 줄바꿈, 텍스트 길이)은 두 프롬프트에 모두 포함.

**Alternatives considered**:
- 하나의 프롬프트에 조건문: 프롬프트 복잡도 증가, Claude 혼동 가능
- 규칙별 모듈화: 오버엔지니어링, 현재 2종 프롬프트로 충분

## R-006: Remotion sceneVideos 통합

**Decision**: `renderer.py`에 `scene_videos` 파라미터 추가. 비디오 파일을 `public/`에 복사하고 props에 `sceneVideos: [{sceneId, videoFile}]` 추가. Remotion 측 `ShortsComposition.tsx`와 `SceneWithVideo.tsx`는 이미 구현되어 있어 props만 전달하면 동작.

**Rationale**: 코드베이스 조사 결과:
- `ShortsComposition.tsx` (line 35): `sceneVideos?: SceneVideo[]` prop 이미 존재
- `SceneWithVideo.tsx`: `OffthreadVideo` 기반 렌더링 컴포넌트 완성
- 비디오 우선 로직 (line 86): `if (videoFile) → SceneWithVideo` 이미 구현
- Python renderer.py만 sceneVideos를 props에 추가하면 즉시 동작

**Alternatives considered**:
- Remotion 컴포넌트 재작성: 불필요, 이미 완성됨

## R-007: Constitution 원칙 I (Zero-Cost) 위반 검토

**Decision**: Seedance API ($0.05/5초 720p)는 원칙 I 위반이나, Phase 6에서 허용. 비용 정당화 필요.

**Rationale**: 원칙 I 원문: "유료 AI 영상 생성 금지 (Phase 1-2)". Phase 6에서는 명시적 금지 없음. 다만 "유료 API 도입은 무료 대안이 없음을 증명한 후에만 허용" 조건 충족 필요:
- 무료 AI 영상 생성 대안: 현재 없음 (Stable Video Diffusion 로컬은 GPU 필요, M1 Mac에서 실용적이지 않음)
- 비용 통제: 영상 모드는 선택적(opt-in), 기본값은 이미지 모드(기존 비용 유지)
- 사용자 비용 투명성: 생성 전 예상 비용 표시 (FR-006)

**Alternatives considered**:
- 로컬 영상 생성 (Stable Video Diffusion): GPU 필요, M1 Mac 비실용적
- 영상 모드 제외: Phase 6 핵심 목표 미달성
