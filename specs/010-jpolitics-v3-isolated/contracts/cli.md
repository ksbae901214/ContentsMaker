# Contract: CLI — `python3 -m src.jpolitics.main`

V3 격리 모드 CLI entry. **`src/main.py` 무관 — 독립 entry point**.

## 명령 형식

```bash
# YouTube URL 모드
python3 -m src.jpolitics.main <youtube_url> [--output-dir DIR]

# 주제 입력 모드
python3 -m src.jpolitics.main --source-type topic \
    --topic "<주제>" \
    [--tone "<톤>"] \
    [--details "<상세>"] \
    [--output-dir DIR]

# 부분 실행
python3 -m src.jpolitics.main <youtube_url> --plans-only
python3 -m src.jpolitics.main <youtube_url> --select-plan 2  # 사용자 선택 자동화
python3 -m src.jpolitics.main --script-file <path> --render-only
```

## 인자

| 인자 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `youtube_url` | str (positional) | — | YouTube 영상 URL (`--source-type youtube`일 때 필수) |
| `--source-type` | `youtube` \| `topic` | `youtube` | 입력 모드 |
| `--topic` | str | — | 주제 모드 입력 (FR-007) |
| `--tone` | str | `"분노·격앙"` | 주제 모드 톤 |
| `--details` | str | `""` | 주제 모드 상세 설명 |
| `--output-dir` | path | `data/jpolitics/{ts}_{slug}/` | 출력 디렉토리 (자동 생성) |
| `--plans-only` | flag | False | 3 plans 생성만 (영상 X) |
| `--select-plan` | 1\|2\|3 | — | 자동 선택 (CLI 비대화형) |
| `--script-file` | path | — | 기존 script.json 로드 |
| `--render-only` | flag | False | TTS + 렌더만 (planner X) |

## 표준 흐름 (전체 파이프라인)

```
1. transcript 추출 (yt-dlp / Whisper / Gemini Files API 폴백 체인)
2. Stage A Gemini 호출 → 3 angle + layout_classification
3. Stage B Claude 호출 → 3 plans
4. 사용자 선택 (CLI 인터랙티브 prompt 또는 --select-plan)
5. politician_card 페치 (필요한 카드 인물명만)
6. plan_to_script → JpoliticsScript
7. TTS 합성 (InJoonNeural +22% 락인)
8. Remotion V3 렌더 → video.mp4
9. 3줄 요약 + 해시태그 생성 → summary.txt
10. 결과 출력 (영상 경로, 재생 시간, 요약)
```

## 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | 정상 완료 |
| 1 | 일반 오류 |
| 2 | 입력 검증 실패 (URL 형식, 필수 인자 누락) |
| 3 | transcript 추출 실패 |
| 4 | Planner 실패 (Gemini/Claude API 오류) |
| 5 | TTS 합성 실패 |
| 6 | Remotion 렌더 실패 |

## 출력 형식

### stdout (성공)

```
[1/10] transcript 추출 중...
[2/10] Stage A 분류 중... (layout=vs_2way)
[3/10] Stage B 기획안 생성 중...
[4/10] 기획안 3개 생성 완료
  1. [title_anchor] 주제: ...
  2. [audience_resonance] 주제: ...
  3. [comparison] 주제: ...
선택 (1/2/3) > 2
[5/10] 인물 카드 페치 중... (양향자, 추미애)
[6/10] 스크립트 생성 완료 (5 씬)
[7/10] TTS 합성 중... (InJoonNeural +22%)
[8/10] Remotion 렌더 중...
[9/10] 요약 생성 중...
[10/10] 완료

영상: data/jpolitics/20260605_104530_경기지사_대결/video.mp4
재생 시간: 52.3초
요약: data/jpolitics/20260605_104530_경기지사_대결/summary.txt
```

### summary.txt (FR-032)

```
[3줄 요약]
양향자 후보의 첫 공격에 추미애 후보가 즉답으로 맞섰다.
경기도지사 자리를 둘러싼 양 후보의 대결 구도가 본격화됐다.
민주당과 국민의힘의 정치 색깔이 영상 한 장면에 응축됐다.

[해시태그]
#양향자 #추미애 #경기도지사 #지방선거 #민주당 #국민의힘 #정치 #2026선거
```

## 인자 검증 규칙

- `youtube_url`이 YouTube 도메인이 아니면 종료 코드 2.
- `--source-type topic` 시 `--topic` 누락이면 종료 코드 2.
- `--select-plan` 값이 1~3이 아니면 종료 코드 2.
- `--script-file` 경로 미존재면 종료 코드 2.

## 격리 보증

- `src/main.py`의 어떤 서브커맨드도 V3에 영향 없음.
- V3 실행 중 V1/V2 CLI 동시 실행 가능 (격리 디렉토리 사용).
