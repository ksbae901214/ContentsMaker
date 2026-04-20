# Research: TRIM-01

**Feature**: NATV 씬 구간 드래그 트리밍
**Date**: 2026-04-20

## R-1 · 타 도구 트리밍 UX 비교

| 도구 | 방식 | 데이터 표현 | 우리 적합성 |
|---|---|---|---|
| Vrew | 타임라인 + 문장(씬) 단위 핸들 | 문장 객체에 start/end | ◎ 씬 구조 동일 |
| CapCut / Premiere | 클립 양끝 트림 핸들, ripple/roll | 프레임 단위 in/out | △ 독립 씬 구조라 ripple 불필요 |
| Descript | 대본 편집 기반 (텍스트 삭제 → 영상 삭제) | 전사 연동 | ✗ 현재 우리는 TTS 분리 구조 |
| Remotion `<Video startFrom endAt>` | 오프셋 prop, 클라이언트 재생 시 트리밍 | 프레임 번호 | ◎ **엔진 레벨 지원** |

**Decision**: Vrew 스타일 UX + Remotion 오프셋 엔진. 파일 재인코딩 없음.

**Rationale**: 우리 `Scene` 는 이미 문장 단위 객체이고 Remotion 은 offset 재생을 네이티브 지원. 재인코딩을 회피하면 저장 비용이 JSON write 한 번으로 끝남.

**Alternatives considered**:
- ffmpeg 실시간 재커팅 → 편집마다 수 초 소요, 저장소 누적 부담
- Descript 스타일 전사 편집 → 구조 변경 범위 너무 큼
- CapCut ripple → 씬간 순서·길이 연동이 우리 TTS 타이밍과 충돌

## R-2 · Remotion `<Video startFrom endAt>` 동작 확인

**Decision**: `startFrom` / `endAt` 은 프레임 번호(입력 FPS 기반). 우리 FPS=30 고정이라 `Math.round(sec * 30)` 으로 충분.

**Rationale**: Remotion 공식 문서 확인 — `startFrom` 은 "몇 프레임 이후부터 재생", `endAt` 은 "몇 프레임에서 끊기". VFR(가변 FPS) 소스는 내부적으로 CFR 로 디코딩되므로 오차는 1프레임 이하.

**Alternatives considered**:
- `trimBefore` / `trimAfter` (Remotion 4 alias) — 동일 기능, 더 명확한 이름이지만 버전 호환을 위해 `startFrom`/`endAt` 유지
- Sequence `from` 으로 대체 → offset 아니라 타임라인 위치 이동이라 의미 다름

## R-3 · 듀얼 레인지 슬라이더 접근성

**Decision**: 외부 라이브러리(react-range, rc-slider) 대신 직접 구현. `role="slider"` 두 개 + `aria-valuemin/max/now` + 키보드 화살표.

**Rationale**:
- 번들 경량화 (라이브러리 15-30KB 절약)
- 프리뷰 `<video>` 연동이 단순 (상위에서 state 관리)
- WAI-ARIA Authoring Practices 1.2 dual-thumb slider 패턴 그대로 준수

**접근성 체크리스트**:
- 핸들 두 개 각각 `role="slider"`, `aria-label="시작 지점"`/`"종료 지점"`
- `aria-valuetext` 에 "분:초" 표시
- 탭 이동, ← → 키로 1초, Shift+← → 로 0.1초
- 최소 타깃 44x44px (모바일 허용 여지)

**Alternatives considered**:
- rc-slider dual mode → 접근성은 좋지만 비디오 프리뷰 통합에 커스텀 render 필요
- react-range → API 가 hook 중심이라 프리뷰 시크 이벤트와 섞기 번거로움

## R-4 · 씬 split / merge 시 오프셋 승계

**Decision**:
- **split**: text 비율 대신 **시간 비율** 로 분할. `ratio = duration_a / duration_total` → `source_mid = source_start + (source_end-source_start) * ratio`. 양쪽 씬에 각각 `(start, mid)`, `(mid, end)` 배정.
- **merge**: 두 씬이 같은 source_video + 인접 offset 이면 `(start_a, end_b)` 로 결합. 다른 source_video 면 병합 거부(현재 로직 유지).

**Rationale**: 기존 `scene_split` 은 display text 길이 비율로 분할했는데, 오프셋은 **시간 단위**이므로 duration 비율이 더 자연스럽고 오차가 작다.

**Alternatives considered**:
- text 비율 유지 → 문장 길이가 씬 재생 시간과 무관할 수 있어 오프셋이 엉뚱한 곳에 떨어짐
- merge 시 두 씬 오프셋이 비인접이어도 강제 결합 → 사용자가 의도치 않은 구간 손실 가능, 거부가 안전

## 결론

모든 NEEDS CLARIFICATION 해소. Phase 1 Design 진행 가능.
