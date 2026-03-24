# Data Model: BGM + 자막 줄바꿈 + URL 소스 확장

## 기존 모델 변경

### Scene (변경)

기존 필드에 2개 추가:

| 필드 | 타입 | 설명 | 변경 |
|------|------|------|------|
| id | int | 씬 번호 | 기존 |
| timestamp | float | 시작 시간(초) | 기존 |
| duration | float | 길이(초) | 기존 |
| type | str | title/body/comment | 기존 |
| text | str | 화면 표시 텍스트 | 기존 — **`\n`으로 줄바꿈 포함** |
| voice_text | str | TTS 읽을 텍스트 | 기존 |
| emphasis | str | high/medium/low | 기존 |
| **highlight_words** | **list[str]** | **하이라이트 대상 단어** | **신규** |

### ShortsScript (변경 없음)

기존 구조 유지. Scene의 highlight_words가 추가되지만 ShortsScript 자체는 변경 없음.

## 신규 모델

### BGM 설정 (voice_config.py에 추가)

| 감정 | BGM 파일명 | 분위기 |
|------|-----------|--------|
| funny | funny.mp3 | 경쾌, 밝은 |
| touching | touching.mp3 | 잔잔, 따뜻한 |
| angry | angry.mp3 | 긴장감, 드라마틱 |
| relatable | relatable.mp3 | 편안, 일상적 |

### URL 파서 결과

URL 파서는 기존 `BlindPost` 모델을 그대로 출력. 신규 모델 불필요.

```
URL 입력 → 사이트 감지 → 파서 선택 → BlindPost 반환
```

### 사이트 감지 매핑

| URL 패턴 | 파서 |
|----------|------|
| `dcinside.com` 포함 | dcinside.py |
| `pann.nate.com` 포함 | natepann.py |
| `cafe.naver.com` 포함 | naver_cafe.py |
| 그 외 | UnsupportedSiteError |

## Remotion Props 변경

### ShortsCompositionProps (변경)

| Prop | 타입 | 변경 |
|------|------|------|
| scriptData | ShortsScriptData | 기존 — scenes에 highlightWords 추가 |
| audioFile | string | 기존 |
| sceneImages | SceneImage[] | 기존 |
| **bgmFile** | **string** | **신규 — BGM 파일명 (빈 문자열이면 BGM 없음)** |

### SceneData (types.ts 변경)

```typescript
// 신규 필드
highlightWords?: string[];  // 하이라이트 대상 단어
```
