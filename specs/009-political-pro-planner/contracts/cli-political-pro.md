# Contract: CLI `python3 -m src.main political-pro`

**Purpose**: 웹 UI 없이 CLI에서 정치 기획안 + 영상 생성을 일괄 실행. 자동화 및 디버깅용.

**Spec Mapping**: FR-001 ~ FR-022 (CLI 진입점)

---

## Usage

```bash
python3 -m src.main political-pro <youtube_url> [options]
```

### Subcommand: `political-pro`

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `<youtube_url>` | (필수) | YouTube URL |
| `--plan-idx <0|1|2>` | (필수, 인터랙티브 미사용 시) | 사용할 plan 인덱스 |
| `--interactive` | `false` | 3개 plan 출력 후 사용자에게 선택 입력 받음 |
| `--plans-only` | `false` | 기획안만 생성하고 종료 (영상 생성 안 함) |
| `--script-only` | `false` | 스크립트까지만 생성하고 종료 |
| `--no-bgm` | `false` | BGM 비활성화 |
| `--no-transitions` | `false` | 트랜지션 비활성화 |
| `--no-sfx` | `false` | 효과음 비활성화 |
| `--output-dir <path>` | `data/political_pro/{ts}/` | 결과 출력 디렉토리 |

---

## Output Format

### `--plans-only`

stdout에 3개 plan을 JSON 단일 객체로 출력:

```json
{
  "plans": [...],
  "videoPath": "...",
  "videoDurationSec": 612.4,
  "transcriptPath": "...",
  "videoTitle": "..."
}
```

### `--interactive`

```
🎬 영상 다운로드 중... (URL: ...)
✅ 다운로드 완료 (10:12)
🎙️ Transcript 확보 중 (VTT) ... 124줄
✅ Transcript 저장: data/political_pro/.../transcript.json

🤔 3개 기획안 생성 중...
✅ 기획안 3개 생성 (Claude, 87초)

────────────────────────────────────────
[Plan 1] angle=title_anchor
  주제: ...
  Hook: "...
  구간: 00:45 ~ 01:15 (30초)
  CTA: ...
[Plan 2] angle=audience_resonance
  ...
[Plan 3] angle=comparison
  ...
────────────────────────────────────────

어떤 기획안으로 영상을 만들까요? (1/2/3): _
```

선택 입력 후 영상 생성까지 진행.

### 전체 실행 (`--plan-idx 0`)

```
✅ 다운로드 완료
✅ Transcript 확보
✅ 3 기획안 생성 (Plan 1 선택됨)
✅ 스크립트 변환 (54초, 12씬)
✅ 씬 클립 분할 (12개, 9:16)
✅ Gemini TTS Charon 합성 (18초)
✅ Remotion 렌더 (62초)

📁 출력: data/outputs/20260513_184500_politicalpro_xyz.mp4 (4.2MB, 54s)
⚠️  주의: 출력은 자동 생성 결과입니다. 게시 전 반드시 사용자 검수가 필요합니다.
```

---

## Exit Codes

| Code | 의미 |
|------|------|
| 0 | 정상 완료 |
| 2 | 입력 검증 실패 (invalid URL, plan-idx 범위 외) |
| 3 | YouTube 다운로드 실패 |
| 4 | Transcript 확보 실패 |
| 5 | Claude 기획안 생성 실패 (2회 시도 모두) |
| 6 | TTS 실패 |
| 7 | 렌더 실패 |
| 1 | 기타 예외 |

---

## Environment Variables

| 변수 | 필수 | 설명 |
|------|------|------|
| `GEMINI_API_KEY` | ✅ (영상 생성 시) | Gemini TTS API 키. 미설정 시 exit 6 |
| `CLAUDE_TIMEOUT_SECONDS` | (선택) | Claude 호출 타임아웃 (기본 1800) |

---

## Acceptance Tests

| 테스트 | 검증 항목 |
|--------|-----------|
| `T1: plans-only happy path` | `--plans-only` → JSON에 plans.length=3 + 모든 angle 다름 |
| `T2: full pipeline` | `--plan-idx 0` → exit 0, mp4 파일 존재, 30~60s |
| `T3: invalid URL` | `not-a-url` → exit 2 |
| `T4: no API key` | `GEMINI_API_KEY` 미설정 + 영상 생성 시도 → exit 6 |
| `T5: plan-idx out of range` | `--plan-idx 3` → exit 2 |
