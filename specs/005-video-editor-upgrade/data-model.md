# Data Model: 영상 제작/편집 기능 고도화

## Entity Diagram

```
Project (1) ──── (1) ShortsScript
                        │
                    (1..N) Scene
                        │
                    ┌────┼────┬──────────┐
                    │    │    │          │
            SubtitleStyle │  Transition  SfxConfig[]
                         │
                   VideoClip (optional)

Template (standalone)
BatchJob (standalone)
```

## Entities

### Scene (기존 모델 확장)

기존 필드 유지 + 새 필드 추가:

| 필드 | 타입 | 설명 | Phase |
|------|------|------|-------|
| id | int | 씬 고유 번호 | 기존 |
| timestamp | float | 시작 시점 (초) | 기존 |
| duration | float | 지속 시간 (초) | 기존 |
| type | str | title/body/comment | 기존 |
| text | str | 화면 표시 텍스트 | 기존 |
| voice_text | str | TTS 읽을 텍스트 | 기존 |
| emphasis | str | high/medium/low | 기존 |
| highlight_words | list[str] | 강조 단어 | 기존 |
| visual_type | str | "image" / "video" / "none" (기본: "image") | P2 |
| motion_prompt | str / None | AI 영상 생성용 모션 프롬프트 | P2 |
| subtitle_style | SubtitleStyle / None | 자막 스타일 (None이면 전역 설정 사용) | P1 |
| transition | TransitionConfig / None | 다음 씬으로의 전환 효과 | P2 |
| sfx | list[SfxConfig] | 효과음 목록 (빈 리스트 기본) | P3 |

### SubtitleStyle (신규)

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| font_family | str | "Noto Sans KR" | 폰트 |
| font_size | int | 55 | 크기 (px) |
| font_weight | str | "bold" | 굵기 |
| color | str | "#FFFFFF" | 텍스트 색상 |
| shadow | str | "3px 3px 8px rgba(0,0,0,0.7)" | 그림자 |
| position_y | float | 0.6 | 수직 위치 (0=상단, 1=하단) |
| bg_color | str / None | None | 배경 색상 (None이면 없음) |
| bg_opacity | float | 0.0 | 배경 투명도 (0-1) |

### TransitionConfig (신규)

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| type | str | "fade" | fade/slide-left/slide-up/zoom/dissolve/wipe |
| duration | float | 0.5 | 전환 시간 (초, 0.3-1.0) |

### SfxConfig (신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| name | str | 효과음 파일명 |
| category | str | surprise/laugh/touching/emphasis |
| offset_ms | int | 씬 시작 기준 재생 시점 (ms) |
| volume | float | 볼륨 (0-1, 기본 0.2) |

### VideoClip (신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| path | str | 생성된 영상 파일 경로 |
| duration_ms | int | 영상 길이 (ms) |
| resolution | str | "720p" / "1080p" |
| cost_usd | float | 생성 비용 ($) |
| source_image | str / None | I2V 원본 이미지 경로 |
| prompt | str | 생성에 사용된 프롬프트 |

### Project (신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| id | str | UUID |
| name | str | 프로젝트 이름 (기본: 영상 제목) |
| created_at | str | 생성 시각 (ISO 8601) |
| updated_at | str | 마지막 수정 시각 |
| script | ShortsScript | 스크립트 전체 |
| image_paths | dict[int, str] | 씬 ID → 이미지 경로 매핑 |
| video_paths | dict[int, str] | 씬 ID → 영상 클립 경로 매핑 |
| audio_path | str / None | TTS 오디오 경로 |
| output_path | str / None | 최종 렌더링 결과 경로 |
| template_name | str / None | 적용된 템플릿 이름 |

### Template (신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| name | str | 템플릿 이름 |
| subtitle_style | SubtitleStyle | 자막 스타일 |
| transition | TransitionConfig | 트랜지션 설정 |
| voice | str | TTS 음성 이름 |
| bgm_enabled | bool | BGM 활성화 여부 |

### BatchJob (신규)

| 필드 | 타입 | 설명 |
|------|------|------|
| id | str | UUID |
| input_type | str | "url" / "text" / "file" |
| input_data | str | URL, 텍스트, 또는 파일 경로 |
| status | str | pending/processing/completed/failed |
| progress | float | 진행률 (0-1) |
| project_id | str / None | 생성된 프로젝트 ID |
| error | str / None | 실패 시 에러 메시지 |
| created_at | str | 생성 시각 |

## Validation Rules

- SubtitleStyle.font_size: 20-120 범위
- SubtitleStyle.position_y: 0.0-1.0 범위
- SubtitleStyle.bg_opacity: 0.0-1.0 범위
- TransitionConfig.duration: 0.3-1.0 범위
- TransitionConfig.type: 허용된 6종 중 하나
- SfxConfig.volume: 0.0-1.0 범위, TTS 대비 0.2 이하 권장
- Scene.visual_type: "image" / "video" / "none" 중 하나
- BatchJob.status: pending/processing/completed/failed 중 하나

## State Transitions

### BatchJob Lifecycle
```
pending → processing → completed
                    → failed
```

### VideoClip Generation
```
requested → generating → completed → integrated (Remotion에 포함)
                      → failed → fallback_to_image
```
