# 정보쇼츠 V1.0 (`info_v1`, 045)

판화 일러스트 + 여성 TTS 약 2분 지식 스토리텔링. 벤치마크는 인스타 @hamster.743606
(공개 12편 실측 — `reports/hamster743606 인스타 계정 분석.md`).

**독립 포맷이다.** 정치쇼츠(V2.1~V5.0)의 렌더러·게이트(039/040/044)·카테고리 원장을 쓰지 않는다.
config 도 `political_v2_configs/` 가 아니라 이 폴더에 둔다.

## 제작 순서

```bash
C=scripts/info_v1_configs/<날짜>_<slug>_info_v1.json
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C validate   # 차단·경고 확인
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C images     # ChatGPT 웹으로 빠진 일러스트 생성
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C sheet      # 컷 미리보기 (렌더 전 눈 확인)
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C render     # Gemini Kore TTS 1회 → Remotion → 썸네일 PNG
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C thumbnail  # 썸네일만 (TTS 불필요)
PYTHONPATH=. .venv311/bin/python scripts/render_info_v1.py $C render --reuse-tts  # 화면만 고칠 때 (문구 바꿨으면 금지)
```

- 산출물: `data/info_v1/<slug>/` (`images/chapter_XX.png`, `tts_raw.*`, `<slug>.mp4`, `<slug>_thumbnail.png`, `_verify/sheet.jpg`)
- 완료 블록은 **유튜브 / 인스타그램 / 틱톡** 3개로 나뉘어 출력된다 — 채팅엔 그대로 인용한다.
- `images` 는 **빠진 장만** 만든다. 마음에 안 드는 장은 파일을 지우고 다시 돌린다.
- 자동화가 실패한 장은 프롬프트가 출력된다 → ChatGPT 에서 직접 만들어 같은 파일명으로 저장.
  `prompts` 명령으로 전체 프롬프트를 볼 수 있다.
- 최초 1회: `python3 -m src.main chatgpt_login` (ChatGPT Plus 로그인, 감지되면 창이 저절로 닫힌다).

## config

| 키 | 필수 | 설명 |
|---|---|---|
| `format` | ✅ | `"info_v1"` |
| `slug` | ✅ | 영문 소문자·숫자·`_` |
| `title` | ✅ | 상단 고정 제목. 줄당 11자, 2줄 이내 |
| `topic_type` | | `paper`(논문 1편) / `story`(기본) |
| `fact_sources` | paper 면 ✅ | `[{label, url}]`. 나무위키 차단 |
| `yt_title` | 권장 | 유튜브·틱톡 제목 (100자 이내) |
| `description` | 권장 | 업로드 설명 2~3줄. 출처(`fact_sources`)·해시태그는 플랫폼별 블록에 자동으로 붙는다 |
| `hashtags` | 권장 | `#` 으로 시작 |
| `caption` | | (구) 설명 — `description` 없을 때만 쓴다 |
| `watermark` | | 기본 `made by 호기심 도감` (채널명) |
| `tts_speed` | | 기본 1.3 (Gemini Kore 1.0배는 5.6음절/초로 느리다) |
| `image_mood` | | 전 장 공통 캐릭터 분위기(영문). 예: 귀엽게 → `adorable chubby kawaii ...` |
| `chapters[]` | ✅ | 3~12개 (벤치마크 7~9, 표준 8) |
| `chapters[].sentences` | ✅ | 문장 = 자막 큐 단위. 길면 쉼표에서 자동 분할 |
| `chapters[].image_prompt` | ✅* | 영문 장면 묘사. 판화 화풍·크림 배경·글자 금지 문구는 자동으로 붙는다 |
| `chapters[].image` | | 직접 만든 이미지 경로 (있으면 `image_prompt` 생략 가능) |
| `chapters[].zoom_at` | | 줌(3.5초 1회)을 시작할 문장 번호. 기본 1 (문장 1개면 0) |
| `chapters[].motion` | | `false` 면 줌 없음. 챕터 0(커버)은 항상 정지 |

## 게이트

- **차단**: format·slug·title 누락, 챕터 3개 미만/12개 초과, 문장 없는 챕터, 프롬프트·이미지 둘 다 없는 챕터,
  paper 인데 출처 없음, 나무위키 출처, 추정/실측 길이 180초 초과.
- **경고**: 챕터 7~9개 밖, 길이 95~135초 밖, 질문형 훅, CTA 문구, 제목 3줄 이상, caption 없음.

## 대본 규칙 (벤치마크 상위 편 기준)

1. 커버 훅은 **사건·숫자 또는 역설 단정문**. 질문형·인사·일반론("한국인에게 ~는") 금지.
2. 본문 장은 짧은 소제목형 첫 문장 → 사실 3~5문장 → 게임·자동차·직장 비유 펀치 1문장.
3. 마지막은 "정리하면/결국" + 아이러니 펀치라인. **CTA 없음.**
4. 짧을수록 좋았다 — 상위 4편 중앙 122초·1,057자, 하위 5편 147초·1,258자.
5. 사실은 출처로 확인 가능한 것만. LLM 요약은 과일반화가 잦다 — 논문형은 초록·결론과 대조할 것.
6. 일러스트는 새로 생성한다. 논문 도표·사진을 가져다 쓰지 않는다.

## 규격 (1080×1920, 벤치마크 720×1280 실측 ×1.5)

크림 `#F6EFE1` · 제목 Black Han Sans 84px · 이미지 박스 x42 y366 993×930 · 자막 Pretendard SemiBold 57px
`#120E0A` 박스 없음, 첫 줄 상단 y1338, 최대 3줄 · 워터마크 우하단 · 하드컷 · BGM/SFX 없음 ·
폰트는 `src/video/remotion/fonts/`(OFL)에서 렌더 시 `public/fonts/` 로 복사된다.
