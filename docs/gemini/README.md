# Gemini 이식 문서

ContentsMaker의 정치쇼츠 워크플로를 Gemini(또는 다른 대화형 AI)에서 쓰기 위한 문서 묶음.

| 파일 | 용도 | 어디에 쓰나 |
|---|---|---|
| `01-pipeline-guide.md` | 상세 매뉴얼 — 뉴스 수집부터 업로드까지 7단계 + 상수·명령 전부 | Gem **지식 파일**로 업로드 / 새 프로젝트 구현 명세 |
| `02-gem-instructions.md` | 압축 지침 (붙여넣기용) | Gemini > Gem 만들기 > **지침** 칸 |
| `03-prompt-templates.md` | 단계별 복붙 프롬프트 7종 | 대화창에 순서대로 입력 |

## 빠른 시작 (Gemini)

1. Gemini에서 **Gem 만들기** → `02-gem-instructions.md`의 `---` 사이 본문을 지침에 붙여넣기
2. 지식 파일로 `01-pipeline-guide.md`, `03-prompt-templates.md`,
   `scripts/political_v2_configs/_template_v2_2.json` 업로드
3. `03-prompt-templates.md`의 프롬프트 1(소재 판정)부터 순서대로 진행
4. 프롬프트 6에서 나온 config JSON을 `scripts/political_v2_configs/`에 저장 후 로컬 렌더

```bash
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> download
PYTHONPATH=. .venv311/bin/python scripts/render_political_v2_2.py <config.json> render
```

Gemini는 기획·대본·제목·CTA·검수를 맡고, 다운로드·컷·렌더는 로컬 `yt-dlp`/`ffmpeg`가 한다.
정치 콘텐츠는 코드에도 가드가 있듯 **자동 업로드하지 않는다** — 사람이 검수 후 수동 업로드.
