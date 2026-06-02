# Feature Specification: Video Module (Remotion)

**Feature Branch**: `003-video-remotion`
**Created**: 2026-03-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - script.json + voice.mp3 → 쇼츠 영상 생성 (Priority: P1)

script.json(씬 타임라인)과 voice.mp3(음성)를 입력받아, 9:16 세로 영상(1080x1920)으로 렌더링한다. 텍스트 애니메이션 + 감정별 그라데이션 배경 + 음성이 합성된 MP4 파일을 출력한다.

**Why this priority**: 파이프라인의 최종 산출물. 이것이 없으면 쇼츠 콘텐츠를 만들 수 없다.

**Independent Test**: `python3 -m src.main render --script data/scripts/sample.json --audio data/audio/sample.mp3` → `data/outputs/sample.mp4` 생성 확인.

**Acceptance Scenarios**:

1. **Given** script.json + voice.mp3, **When** 렌더링 실행, **Then** 9:16 세로 MP4가 `data/outputs/`에 생성된다
2. **Given** funny 감정 스크립트, **When** 렌더링하면, **Then** 노란/주황 그라데이션 배경이 적용된다
3. **Given** 5개 씬이 포함된 스크립트, **When** 렌더링하면, **Then** 각 씬이 타임라인에 맞게 순차 표시된다
4. **Given** 음성 파일, **When** 렌더링하면, **Then** 텍스트 전환과 음성이 동기화된다

---

### User Story 2 - 통합 파이프라인: raw → script → voice → video (Priority: P2)

CLI 한 줄로 raw_content.json부터 최종 MP4까지 전체 파이프라인을 실행한다.

**Acceptance Scenarios**:

1. **Given** raw_content.json, **When** `python3 -m src.main pipeline --file raw.json` 실행, **Then** script.json + voice.mp3 + final.mp4 모두 생성

---

### Edge Cases

- voice.mp3 없이 렌더링 → 무음 영상 생성 (배경음만)
- 씬이 1개뿐인 스크립트 → 정상 렌더링
- 매우 긴 텍스트 → 폰트 크기 자동 축소

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템 MUST script.json + voice.mp3를 입력받아 9:16(1080x1920) MP4를 생성한다
- **FR-002**: 시스템 MUST 감정별 그라데이션 배경을 적용한다
- **FR-003**: 시스템 MUST 씬 타임라인에 맞춰 텍스트를 순차 표시한다
- **FR-004**: 시스템 MUST 텍스트에 fadeIn 애니메이션을 적용한다
- **FR-005**: 시스템 MUST 음성 파일을 영상에 합성한다
- **FR-006**: 시스템 MUST Noto Sans KR 한국어 폰트를 사용한다
- **FR-007**: 시스템 MUST 30fps, h264 코덱으로 렌더링한다
- **FR-008**: 시스템 MUST 결과를 `data/outputs/`에 저장한다

## Success Criteria *(mandatory)*

- **SC-001**: script.json + voice.mp3 → MP4 렌더링이 5분 이내에 완료된다
- **SC-002**: 생성된 MP4가 9:16 비율(1080x1920)이다
- **SC-003**: 텍스트가 화면 중앙에 가독성 있게 표시된다
- **SC-004**: 4종 감정 각 1개씩 영상 생성 시 배경색이 구별된다
