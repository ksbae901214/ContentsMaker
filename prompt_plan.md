# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-08-13

---

## 🚧 신규: 카테고리 확장 — 정치 외 경제·사회·연예 (036) — 2026-08-13

> 사용자 요청: "정치이슈 이외에 다른 경제 사회 연예 이슈도 다루려고 해 어떻게 업그레이드 하면 좋을지 기획해줘"
> **상태**: Phase 0(계측) 구현 완료. Phase 1~4 미착수 (사용자가 "Phase 0만 먼저" 선택).

### 핵심 판단
새 파이프라인을 만들지 않는다. 렌더러·길이 캡(38~42초)·육성 릴레이 구조·CTA 삽입
로직은 도메인과 무관하므로 **V2.2 제작 표준에 `category` 축 하나를 관통**시킨다.
실제로 달라지는 건 4가지뿐: ①소재 프레임 어휘 ②CTA 선택지 축 ③제목 앵커
④클립 소스 저작권 등급.

035의 '결과가 난 사건' 프레임은 도메인이 바뀌어도 그대로 산다 — 어휘만 갈아끼운다
(경제: 동결·급락·파산 / 사회: 무죄·구속·폐지 / 연예: 인정·하차·복귀).

### 사용자 확정 결정 (2026-08-13)
| 항목 | 확정 | 비고 |
|---|---|---|
| 채널 구조 | **단일 채널 혼합** | 권장안(2채널 분리)과 다름 — 혼합 희석 위험을 계측으로 감시 |
| 도입 카테고리 | **경제 + 사회 + 연예 전부** | 우선순위는 경제 → 사회 → 연예 |
| 이번 세션 범위 | **Phase 0만** | 계측 없이 확장하면 판정 불가 |

### 기존 자산 / 격차
- AI 플래너 라인(`political_pro` topic 모드)엔 `category: political|economic` 이
  2026-07-02에 이미 관통돼 있다 (Stage A/B 프롬프트·`ShortsPlan.category`·API·UI).
- **격차**: 매일 쓰는 라인은 그쪽이 아니라 수동 config + `render_political_v2_1/2.py`.
  034/035 게이트가 전부 정치 어휘로 하드코딩돼 있다.

| 위치 | 정치 하드코딩 | Phase |
|---|---|---|
| `political_upload_package.py` `_CLASH_WORDS`/`_OUTCOME_WORDS` | 사퇴·부결·경질 | 1 |
| `political_upload_package.py` `DEFAULT_PINNED_COMMENT` | "① 여당 ② 야당" | 1 |
| `political_upload_package.py` `lint_yt_title` | 제목에 `persons`(실명) 요구 — 경제는 숫자·기업명이 앵커 | 1 |
| `political_cta.py` `SIDE_PICK_MARKERS` | ①/② 마커는 재사용 가능, 예시 문구만 도메인별 | 1 |
| `political_length.py` | 없음 — 38~42초 캡은 도메인 무관 | **무변경** |
| `render_political_v2_2.py` | 없음 (이름만 정치) | 기본값만 |

### 도메인별 4축 (Phase 1 설계 근거)
| | 결과어 | CTA 선택지 축 | 제목 앵커 | 소스/저작권 |
|---|---|---|---|---|
| 정치 | 사퇴·부결·철회·경질 | 여당/야당 | 실명 1~2 | 국회방송·기자회견 (공적 발언) |
| 경제 | 동결·인상·급락·파산·리콜 | 살까/팔까, 정책 찬반 | 숫자+기업·기관명 | 뉴스·기관 발표·차트 (**최저 위험**) |
| 사회 | 무죄·구속·판결·폐지·사과 | 처벌 과하다/약하다 | 사건명+결과 | 뉴스 화면 (2차 가해 리스크) |
| 연예 | 인정·결별·하차·복귀·폭로 | 잘못이다/아니다 | 실명+반전 | 방송 클립 (**최고 위험**) |

### 단계
- [x] **Phase 0 계측 (완료 2026-08-13)** — 아래 참조
- [x] **Phase 1 도메인 규칙 팩 (완료 2026-08-13)** — `scripts/shorts_domain.py` 신설
- [x] **Phase 2 도메인 가드레일 (완료 2026-08-13)** — 차단 1종 + 경고 4종
- [x] **Phase 3 템플릿·문서 (완료 2026-08-13)** — 카테고리별 템플릿 3종 + README.
      **configs 서브폴더 분리는 하지 않음** — 기존 config 37개·문서·메모리가 전부
      현재 경로를 참조해 이동 비용만 크고 얻는 게 없다 (Surgical Changes)
- [ ] **Phase 4 파일럿·판정** — 카테고리당 6편 / 2주 → 아래 기준선 대비 판정.
      **코드 작업이 아니라 운영 작업** (실제 영상 제작·업로드 후 리포트 비교)

### Phase 0 구현 (완료)
- **신규 `scripts/shorts_category.py`** — 카테고리 원장 + 제목 키워드 추론.
  - 원장(권위): `data/channel_analytics/category_ledger.json`. 업로드가 수동이라
    유튜브에 카테고리가 안 남는다 → 로컬 원장이 유일한 정답 소스.
  - 추론(폴백): 과거 편 백필용 best-effort. 한/영 키워드, **해시태그를 신호로 사용**
    (`classify_title` 의 문체 분류가 해시태그를 벗기는 것과 목적이 다름).
  - 제목 매칭: NFC + 해시태그 제거 + 공백 축약 + **접두 일치** — 업로드 시 제목
    뒤에 해시태그·꼬리말이 붙어도 원장 항목을 찾아낸다.
- **`political_upload_package.py`** — `upload_package.md` 에 카테고리 표기 +
  렌더 시 원장 자동 기록(`generate_upload_package(..., ledger_path=)`).
  원장 기록 실패는 경고만 — 계측이 제작을 막지 않는다.
- **`analyze_channel_performance.py`** — `summarize(entries, ledger=)` 에
  `by_category` 추가, 리포트에 카테고리 표 + `category_mix_warnings()`
  (표본 3편 이상, 전체 중앙값의 <70% = 희석 후보 / ≥130% = 확대 후보), `--ledger` 옵션.
- **`render_political_v2_1/2.py`** — `validate_config` 에서 category 오타 fail-fast.

### 기준선 (2026-08-05 스냅샷 88편, 추론 백필)
| 카테고리 | 편수 | 중앙값 | 전체 대비 |
|---|---|---|---|
| political | 73 | 1,174 | 100% |
| economic | 11 | 1,172 | 100% |
| society | 2 | 948 | 81% |
| unknown | 2 | 2,021 | — |

카테고리로는 **아직 아무 차이가 없다** (전부 100% 언저리) — 035의 "병목은 클릭이
아니라 완주율" 결론과 일치. 신규 카테고리는 이 1,17x 선을 넘어야 의미가 있다.
미분류는 88편 중 2편(2%) — 영문 제목 키워드 추가로 39% → 2% 개선.

### 리스크
- **HIGH** 연예 방송 클립 저작권 — 3순위로 미룸. 도입 시 인용 범위 최소화 + 출처 명시 강제
- **MEDIUM-HIGH** 사회 피의사실공표·2차 가해 — 판결 확정 사건 우선
- **MEDIUM** 경제 투자권유(자본시장법) — Phase 2 어휘 게이트
- **MEDIUM** 단일 채널 혼합 시 추천 신호 희석 — `category_mix_warnings` 로 감시
- **MEDIUM** 제작 부하 — 카테고리는 **대체**이지 추가가 아니다. 총 편수 유지
  (035 리포트가 이미 3일 업로드 공백을 경고 중)

### Phase 1/2/3 구현 (완료 2026-08-13)
- **신규 `scripts/shorts_domain.py`** — frozen `DomainRules` × 4 카테고리.
  결과어/공방어·CTA 예시·고정댓글·제목 앵커·emotion/배경색·금지어·주의어·체크리스트를
  한 표로 모았다. 정치 규칙은 `political_upload_package` 의 기존 상수(`_CLASH_WORDS`
  등)를 **그대로 참조** — 두 곳이 갈라지면 035 게이트가 조용히 약해진다.
- **가드레일 2단**:
  - 차단(`gate_domain_words` → ValueError): 경제 투자 권유 13종(매수·매도·추천주·
    급등각·존버·물타기·풀매수·몰빵·수익률 보장…). 유사투자자문 소지라 하드 게이트.
  - 경고(`domain_warnings`): 사회 피의사실 7종 / 연예 미확인 사생활 7종 / 경제 전망
    표현 / 연예 `source_channel` 누락. 사람 판단이 필요한 것들.
  - 둘 다 `"domain_gate": "off"` 로 우회.
- **관통**: `lint_topic_frame`·`is_clash_frame`·`has_outcome_frame`·`lint_yt_title`·
  `resolve_pinned_comment`·`build_upload_package_md`(체크리스트) + `lint_cta(cta, category)`
  + 렌더러 `resolve_emotion_type`/`resolve_bg_colors`.
- **템플릿 3종** — `_template_{economic,society,entertainment}_v2_2.json`.
  전부 validate + CTA 삽입 + 업로드 패키지 생성까지 dry-run 통과(경고 0건).

### 검증 (2026-08-13, Phase 0~3 누적)
- pytest **1764 passed / 1 skipped** (신규 106개: `test_shorts_category.py` 37,
  `test_shorts_domain.py` 28, `test_domain_category_wiring.py` 23,
  `test_upload_package_category.py` 7, `test_channel_performance.py` +11)
- 변경 파일 12개 ruff 통과
- **회귀 실증**: 기존 정치 config **37개 전부** 차단 0 / 경고 0 / 렌더 기본값 변화 0
- 실제 88편 스냅샷 백필 dry-run, 가드레일 4종 발화 확인

### 알게 된 것
034 보도체 게이트(`~했다`류 과거형 어미 차단)는 카테고리 공통이라, 경제 템플릿의
'영끌족은 웃었다' 같은 **서사형 제목도 차단된다**. 게이트를 약화시키는 대신 제목을
명사로 닫도록 템플릿·README에 명시했다 (정치에서 검증된 게이트를 신규 카테고리
편의를 위해 풀지 않는다).

### 복잡도: Phase 0~3 = MEDIUM (실측 일치)

---

## 🚧 신규: 조회수 개선 — 채널 분석 & 패키징 강제화 (034) — 2026-07-30

> 사용자 요청: "내 채널들인데 조회수가 잘 안나오는 것 같아. 내 채널과 다른 정치쇼츠 채널들을 분석하고 어떤 점을 업그레이드하면 좋을지 기획해줘"
> **상태**: 계획 확정 (2026-07-30, 사용자 "진행" 승인).

### 채널 분석 결론 (2026-07-30 실측)

**영상 품질이 아니라 '포장(제목·해시태그)'과 '채널 정체성'이 병목.**

| 채널 | 구독 | 영상 | 조회수 중앙값 | 최고 |
|---|---|---|---|---|
| 국회직캠 (YT) | 339 | 80 | ~1,100 | 7,900 (오세훈 대역전극) |
| 국회직캠 (TikTok) | 364 | 30+ | ~900 | 8,332 |
| 우파전선 (보수 개인, 408명) | 408 | 12 | ~2,800 | 1.4만 |
| 짤막쇼츠 (진보 개인) | 4.51만 | 661 | ~3만 | 148만 |

동일 주제(장동혁·조정식 연임개헌, 7/30 당일): 국회직캠 670회 vs TV조선 4.5천 vs OBS 1.6만.

**격차 원인 5가지**: ① 보도체 제목 + 제목 내 해시태그 8~11개 (경쟁: 12~20자 감정훅 + 0~3개) ② 채널 정체성 혼선 (직캠 이름 + TTS 논평 + 정보성 잡화 혼재) ③ 같은 주제 V2.1/V2.2 병행 업로드 자기잠식 (거의 동일 제목 2건씩 3쌍 확인) ④ 상위=대형 인물 갈등 서사, 하위=정책 설명형 ⑤ 구독 전환 장치 부재 (80편에 339명).

### P1 — 패키징 엔진 강제화 (코드, 효과 즉시)

- `political_upload_package.py`: `sanitize_yt_title()` 신규 — 제목 내 해시태그 자동 제거→설명란 이동. `lint_yt_title` 강화 — 보도체 어미(한다/했다/합니다/입니다…)·보도체 단어(논란/현황/총정리/공방) 감지, 해시태그 잔존 경고.
- `render_political_v2_1.py`/`v2_2.py` `validate_config`: yt_title 보도체·해시태그 포함 시 **차단**(ValueError, fail-fast at load). 탈출구: `"yt_title_lint": "off"`.
- upload_package.md에 업로드 전 체크리스트 추가: 썸네일=인물 표정 절정 컷, 같은 주제 중복 업로드 금지(플랫폼 분리), 제목 A/B 2안(①감정훅형 ②호기심형) 가이드.

### P2 — V2.2 리액션 순간 중심 가이드 (문서)

- configs README·`_template_v2_2.json`: 클립 선정 1순위 = **표정·리액션 절정**(웃음/한숨/야유/침묵/눈물) — 짤막쇼츠 93만회 영상의 공통점은 '발언 내용'이 아니라 '반응 장면'. TTS 팩트 정리(마지막 1씬)는 차별점으로 유지.

### P3 — 채널 운영 전략 (비코드, 결정 반영)

- 정보성 잡화(지원금·물가·금리) 편성 중단 — 정체성 희석 주범.
- V2.1/V2.2 같은 주제 병행 시 **플랫폼 분리**: V2.2→유튜브, V2.1→틱톡 (또는 제목·훅 완전 차별화).
- 인물 우선순위: 이재명·장동혁·오세훈·한동훈·조국 (검색량 상위) 중심 편성.

### P4 — 틱톡 계정 정비 (수동 5분, 즉효)

- 아이디 `user8295918181994` → 브랜드명(예: `gukhoe_fancam`), 소개글 + 유튜브 링크 추가.

### P5 — 성과 루프 강화 (코드)

- `analyze_channel_performance.py`: `classify_title` 보도체 시그널 확장(어미·단어), 제목 해시태그 수 추적(`hashtag_count`) + 해시태그 구간별(0~3 vs 4+) 조회수 요약·리포트 추가 → 2주 후 유형별 검증.

### 리스크

- 상: 감정 훅 제목의 어그로화 ↔ 팩트 신뢰 훼손 — 검수 수칙 유지, 허위·명예훼손 경계.
- 중: 방송사 클립 재사용 저작권 클레임 — "공정 이용 편집물" 고지 검토.
- 하: 제목 lint 차단이 기존 config 재렌더와 마찰 — `yt_title_lint: off` 탈출구 제공.

---

## 🚧 신규: 정치쇼츠 V2.2 — 원본 육성 릴레이 포맷 (033) — 2026-07-23

> 사용자 요청: "현재는 훅이 맨 처음 한 번만 나오는데, 훅(원본 육성) 부분이 많이 나오고 TTS가 의견 말하는 씬은 1~2번만 나오게 V2.2 기획"
> **상태**: ✅ Phase 1~4 구현 + e2e 검증 완료 (2026-07-23). 사용자 선택: TTS 기본 구성 = **중반 논평 1개만** — 결말도 원본 클립로 마무리(직캠 느낌 극대화).
> 신규 파일: `scripts/render_political_v2_2.py`, `scripts/political_v2_configs/_template_v2_2.json`, `tests/test_political_v2_2.py`(32), configs README "V2.2 확장" 섹션.
> 검증: pytest 1545 passed / 0 failed (신규 32), ruff clean, V2.1 무수정. e2e(오세훈 편 소스 재사용, 클립 4 + TTS 1, 26.1s, 클립 비중 73%): 조립 mp3 실측 — 클립 구간 -91dB(TTS 완전 침묵)·TTS 구간 -14dB, 최종 mp4 클립 구간 육성 -18.5dB, 프레임 4장 육안 — 훅 노란 하단 자막·TTS 빨강 강조·`[재판부]`/`[뉴스]` 화자 라벨 모두 정상.
> **실전 1편 + 사용자 구성 확정 (2026-07-23)**: 첫 실전편 = 오세훈 1심 편 V2.2 재제작(`ohsh_yeoron_v2_2.json`, 31s). 사용자 확정 구성: **한 주제에 여야 한마디씩 육성 클립 2개(훅) → TTS 의견 1개**. 제작법: YTN 여야 반응 리포트 1편에서 Gemini 전사(`gemini_transcribe_video`)로 1인칭 종결어미(육성 싱크) 구간 식별 → silencedetect 문장 경계 실측 → 후보 컷 재전사로 발언 확정 → 프레임으로 화자 자막 확인(강준현 민주 vs 박성훈 국힘 수석대변인). 파생 수정: 본문 클립(scene 1+) 상한 10→12s 완화(`CLIP_BODY_MAX_SEC`, 브리핑 끊어읽기 포즈 실측 — 훅은 10s 유지), `resolve_clip_cut` 신규. pytest 1551 passed (신규 +6).
> **립싱크 버그 수정 (2026-07-23, 사용자 리포트 "훅2 싱크 안 맞음")**: 원인 = ① Remotion(OffthreadVideo) 오디오 추출이 AAC priming(2112샘플)을 스킵하지 않아 클립 오디오 **44ms 지연** (교차상관 실측, adelay 대조실험으로 방향 확정 — 1.1배속과 무관, 배속은 TTS에만 적용) ② 씬 경계 반프레임(17ms) 반올림. 수정 = V2.2 전용 `_loudnorm_clip_audio`: loudnorm 후 `aresample=48000` + `atrim=start=0.044`(오디오 44ms 당김, `AAC_PRIMING_COMP_MS`), `resolve_clip_cut` duration 30fps 격자 반올림. 재렌더 실측: S0/S1 모두 **+0ms** (비디오 배치는 자막 전환 스파이크로 정확성 별도 확인). V2.1 훅에도 동일 44ms 지연이 잠재 — V2.1은 무수정 원칙이라 보류, 차기 개선 시 반영.
> 포맷 정의: V2.1(육성 훅 1개 + TTS 나레이션 N개) → V2.2(**육성 클립 3~5개가 영상의 뼈대** + TTS 논평 기본 1개, 최대 2개). 근거: 031 벤치마크 실측 — 직캠형(원본 발언 릴레이) 쇼츠 최고 500만 뷰 vs TTS 브리핑형 수만 뷰 천장. V2.1은 훅만 직캠화했고, V2.2는 본문까지 직캠화하되 채널 아이덴티티(Charon 논평)를 1~2씬으로 보존.

### 편집 포맷 규칙 (콘텐츠 설계)

- 권장 5~7씬, 총 45초 캡: `클립(훅) → 클립 → [TTS 논평] → 클립 → 클립(결말·루프 유도)`
- **클립 씬**: 각 1~10초(문장 완결 — V2.1 훅 규칙 그대로), 원본 오디오(mute=False + loudnorm), 발언 요지 노란 자막 하단 배치. 인접 클립은 **대립 배치**(A 주장 → B 반박 → A 재반박)로 갈등 아크를 원본 육성만으로 구성. 화자 식별용 `speaker` 라벨 자막 접두 옵션.
- **TTS 씬**: 기본 1개(중반 "관점 정리/의견", 5~8초). 최대 2개까지 허용(3개 이상 validate 경고). 결말은 원본 클립로 마무리 — CTA가 필요하면 고정댓글(pinned_comment)로 대체. 배속 1.1 유지.
- 클립 오디오 비중 ≥ 65% 권장 (validate 시 경고).

### Phase 1 — config 스키마 & 스크립트 골격 (난이도 하)

- **신규** `scripts/render_political_v2_2.py` (V2.1 파일 무수정 — 공용 헬퍼 `_probe_dur`/`_download_source`/`_speed_audio`/`_loudnorm_clip_audio` 등은 import 재사용).
- scene 스키마에 `mode: "clip" | "tts"` (기본 tts). clip 씬: `source`/`start_sec`/`duration`/`text`/`hl`(+선택 `speaker`). tts 씬: V2.1과 동일(`voice`/`frac`/`color`/`emph`).
- validate: clip 1~10s, scene 0은 clip 강제(훅), tts 씬 3개 이상이면 경고, 총 길이 45s 초과 경고.

### Phase 2 — 오디오 타임라인 조립 일반화 (핵심, 난이도 중)

- V2.1의 "앞 무음 패딩 1회"를 일반화: TTS는 tts 씬만으로 합성 → silence_align → 배속 → 씬별 세그먼트 컷 → **클립 길이만큼의 무음 블록을 사이사이 삽입해 ffmpeg concat** → 전 씬 global timings 재계산.
- 순수 함수 `build_timeline(scenes, clip_durs, tts_timings) → (audio_segments, global_timings)` 분리 — 단위 테스트 대상.
- Remotion 무수정 (V2.1과 동일 원리: 오디오·타이밍을 렌더 전에 미리 조립).

### Phase 3 — 씬 컷·렌더 통합 (난이도 하)

- clip 씬: `cut_segment(mute=False)` + loudnorm (V2.1 훅 컷 로직을 N회 반복). tts 씬: 기존 mute=True 컷.
- 씬별 검증 산출물: `_verify/scene_NN.png` + clip 씬은 `_verify/clip_NN.mp4` 프리뷰(렌더 전 청음 확인) — 032 P2와 정합.
- 업로드 패키지(`political_upload_package.py`) 그대로 재사용.

### Phase 4 — 템플릿·검증 (난이도 하)

- `_template_v2_2.json` + configs README "V2.2 확장" 섹션.
- e2e: 실전 소재 1편(클립 4 + TTS 2) 렌더 → 육성↔TTS 전환 청음·자막 육안 확인.

### 032와의 관계

- 032 P1 `hook-find`는 V2.2에서 가치 3~5배(클립 다중 탐색). 구현 시 `--source`/`--query` 반복 호출로 그대로 활용 — V2.2 전용 일괄 clip-find는 후속.
- 032 P2(scene `start_sec` 정밀화)는 V2.2 clip 스키마에 자연 포함. P3(펀치인 줌)은 tts 씬에만 적용 권장(육성 씬은 원본 보존).

### 리스크

- 중: 클립 릴레이 시 문맥 단절 → `speaker` 라벨 + 대립 배치 규칙으로 완화
- 중: 클립별 음질 편차 → 클립별 loudnorm + download 단계 청음 확인
- 중: 원본 발언 다중 인용의 편집 왜곡 위험 → 문장 완결 규칙 + 발언 맥락 유지(기존 팩트 교차검증 수칙)
- 하: TTS 분량 감소로 Gemini 일 쿼터 부담은 오히려 감소

### 검증 계획

- Phase 2: `build_timeline` 단위 테스트(클립/무음/TTS 세그먼트 경계·타이밍 합) + ffmpeg concat 산출물 길이 실측
- Phase 4: e2e 1편 — 씬 전환마다 오디오 소스(육성↔TTS) 교차 청음, 자막 위치·색 확인
- 공통: pytest 전체 회귀 + ruff clean, V2.1 스크립트·config 무수정

---

## 🚧 신규: 정치쇼츠 V2.1 추가 개선 (032) — 2026-07-14

> 사용자 요청: "정치쇼츠V2.1 만들어준거 좋은데 여기 더 추가할만한거 있을지 기획"
> **상태**: 계획 확정 (2026-07-14, 사용자 선택: P1·P2·P3 진행. P4 편단위 성과추적·P5 config lint는 보류).
> 진단: V2.1 제작 루틴의 잔여 병목 — ① 훅 구간 선정이 전 과정 최대 수작업(자막 검색→silencedetect 수동 실측→문장 경계 계산) ② 본문 씬이 `frac` 기반 임의 지점 컷(인트로/로고 걸림·프리즈 위험) ③ 031 Phase 4(펀치인 줌) 보류분 미반영.

### P1 — 훅 구간 자동 탐색 `hook-find` (임팩트 최상 / 난이도 중)

- **신규** `scripts/political_hook_finder.py` (순수 로직 분리, 테스트 대상) + `render_political_v2_1.py`에 `hook-find` 서브커맨드 와이어링.
  - `... <config.json> hook-find --source <key> --query "<발언 검색어>"`
- 흐름: yt-dlp `--write-auto-sub --skip-download`로 자막(vtt/srt) 다운로드 → 검색어 매칭 큐 후보 추출 → 다운로드된 `src_<key>.mp4`의 후보 주변(±5s)에 silencedetect(`highpass=f=150,silencedetect=n=-25dB:d=0.15`) 실측 → **문장 끝 휴지 +0.5~0.8s 포함** start_sec/duration 자동 제안 (1~10s 클램프, V2.1 훅 규칙 자동 보장).
- 후보별 프리뷰 클립을 `_verify/hook_candidates/`에 추출 + config `hook` 스니펫 JSON 출력(복붙용).
- 테스트: vtt/srt 큐 파싱, silencedetect 로그 파싱, 문장 경계 스냅 — 순수 함수 단위.
- 리스크(중): 자동 자막 타임스탬프 오차 ±1~2s → silencedetect 실측 보정으로 흡수.

### P2 — 본문 씬 클립 구간 정밀화 (임팩트 상 / 난이도 하)

- scene 스키마에 `start_sec` 직접 지정 지원 (`frac`과 병행, 지정 시 우선) — `cmd_render` 씬 컷 루프 + `validate_config`.
- 렌더 시 **씬별 검증 프레임** `_verify/scene_NN.png` 자동 추출 (현재는 소스당 1장뿐).
- 소스 잔여 길이 < 씬 길이면 프리즈 경고 출력 ([[political-pro-clip-freeze]] 계열 예방).

### P3 — 펀치인 줌 (031 Phase 4 보류분 부활) (임팩트 중상 / 난이도 중)

- `Scene`(script_models.py)에 `zoom` 필드 신규 (snake→camel 변환은 renderer 기존 경로) → `SceneWithVideo.tsx`에서 씬 길이에 걸친 미세 줌인(1.0→1.06).
- 강조 씬(emph=true)은 컷 중간 펀치인 1회(1.0→1.05 스텝) — 030 벤치마크 "컷 리듬 빠르게" 반영.
- config: scene별 `zoom: true/false` (기본 off, 템플릿에 예시). 훅 씬(원본 육성)은 기본 off 유지.
- 리스크(하): 줌 과용 시 어지러움 → 씬당 1회·배율 1.06 상한.

### 검증 계획

- P1: 실제 config 1건(예: `josguk_ilbe.json`) 대상 hook-find 실행 → 제안 구간이 기존 수동 선정값과 ±1s 내 일치 + 프리뷰 클립 청음 확인
- P2: start_sec 지정 씬 렌더 → 씬별 검증 프레임 생성 확인, 짧은 소스로 프리즈 경고 확인
- P3: remotion tsc 0 errors + zoom on/off 각 1편 e2e 렌더 육안 비교
- 공통: pytest 전체 회귀(기존 1510+) + ruff clean, V2.1 기존 config 무수정 하위 호환

---

## 🚧 신규: 정치쇼츠 V2 (수동 템플릿) 조회수 개선 (031) — 2026-07-14

> 사용자 요청: "현재 정치쇼츠V2가 딱 좋은데 이걸 좀더 개선시켜서 더 조회수를 많이 얻게끔 할수 있는 방법이 있을까? 기획해줘"
> **상태**: ✅ Phase 1~3 구현 + 실전 검증 2회 + **사용자 확정: 앞으로 정치쇼츠는 V2.1이 표준** (2026-07-14). V2는 무수정 보존(폴백).
> 실전 검증: ① 이재명 부동산 편(훅=이재명 육성 6s "불로소득 공화국", `leejm_budongsan_v2_1.json`) ② 장윤기/보완수사권 편(훅=김민석 총리 육성 7s "폐지가 정부 기본 입장", `jang_police_power_v2_1.json`). 피드백 반영: 훅 문장 완결 필수(HOOK_MAX 5→10s), 훅 자막 하단 배치(`Scene.subtitle_position="bottom"` 신규 — script_models.py+SceneText.tsx).
> 신규 파일: `scripts/render_political_v2_1.py`, `scripts/political_upload_package.py`, `scripts/analyze_channel_performance.py`, `scripts/political_v2_configs/_template_v2_1.json`, `tests/test_political_v2_1.py`(30), `tests/test_channel_performance.py`(19)
> 검증: pytest 1510 passed / 0 failed (신규 49), ruff clean, 무음 패딩+타이밍 시프트 ffmpeg e2e 확인, V2 config 하위 호환 확인.
> **핵심 판단**: 030의 코드 개선(P1~P4)은 자동 파이프라인(`political_planner.py` 경로)에만 적용됐고, 실제 제작에 쓰는 **수동 V2 템플릿(`scripts/render_political_v2.py`)에는 미반영**. 훅 씬이 여전히 TTS 낭독 + 전 클립 `mute=True`.
> **구현 중 발견**: 자동 P2 경로(commit `9e9e347`)는 훅 클립을 mute=False로 컷하지만 **TTS `<Audio>`가 frame 0부터 재생되고 타이밍 시프트가 없어 훅 원본 음성과 TTS가 겹치는 잠재 버그** 존재. V2.1은 TTS mp3 앞에 훅 길이만큼 무음 패딩 + 타이밍 시프트로 Remotion 무수정 해결.

### Phase 1 — 훅 씬 원본 발언 육성 (임팩트 최상, 난이도 중) — V2.1 신규 스크립트

- **신규** `scripts/render_political_v2_1.py` (V2 기반, V2 파일 무변경): config `hook` 섹션(source/start_sec|frac/duration) 지정 시 scene 0 = 인물의 **실제 발언 오디오**(`cut_segment(mute=False)` + loudnorm) 0초 배치, `yt_title` 노란 자막 오버레이. TTS는 scene 1부터.
- TTS mp3 앞 무음 패딩(adelay) + scene_timings 훅 길이 시프트. `use_intro_bgm=False`로 훅 육성 보호.
- config 스키마 v2.1(`yt_title`/`hook`/`persons` 등) — `scripts/political_v2_configs/README.md`에 추가.

### Phase 2 — 업로드 패키지 자동 생성 (난이도 하)

- 렌더 완료 시 `upload_package.md` 생성: ① "[악역]-[응징]-[주인공]" 공식 제목 + A/B 대안 1개 ② 설명문 ③ #인물명 2~4개 해시태그 ④ 고정댓글 문안 ⑤ 권장 업로드 시각(평일 20~21시) ⑥ 썸네일 후보 프레임 3장.
- FR-020 자동 업로드 차단 유지 — "복붙 준비물"만 생성.

### Phase 3 — 성과 피드백 루프 CLI (난이도 중)

- `scripts/analyze_channel_performance.py`: yt-dlp로 내 채널(UCYNNMfkMW_EZJBp514-DjaA) 쇼츠 전편 조회수·길이·제목 수집(공개 데이터, OAuth 불필요) → 제목 유형(hook형 vs 보도형)·길이 구간·훅 유형별 상관 리포트.
- 030 검증 계획("2주 후 중앙값 비교")의 실행 도구.

### 보류/운영 항목

- Phase 4(펀치인 줌·씬 내 2컷, Remotion) — 이번 범위 제외, 추후 결정.
- 운영 수칙(코드 무관): P0 업로드 리듬 복구(일 1~3편, 20~21시, 2~3주 무공백), 루프형 결말 문장 규칙. P5(직캠 전환)는 V2 포맷 유지 결정으로 제외.

### 리스크

- 중: 원본 발언 클립 오디오 품질(현장 잡음) → loudnorm + 클립 선정 시 음질 확인
- 중: Gemini TTS 일 10회 쿼터 → 기존 캐시 폴백
- 하: 리텐션 지표 API 미제공 → 조회수 프록시 + YouTube Studio 수동 확인

### 검증 계획

- Phase 1: 샘플 config 1편 e2e 렌더 → scene 0에서 원본 육성 재생·자막 오버레이 육안/청음 확인
- Phase 2: 렌더 후 `upload_package.md` 필드 6종 생성 확인
- Phase 3: 실제 채널 대상 실행 → 52편+ 수집·리포트 출력 확인
- 적용 후 2주 P0 리듬 업로드 → 편당 조회수 중앙값(기존 ~1,300) 및 첫 48시간 조회수 비교

---

## 📊 신규: 조회수 부진 원인 분석 및 개선 계획 (030) — 2026-07-03

> 사용자 요청: "생성한 영상들 조회수가 너무 떨어지는데 잘되는 쇼츠들을 분석하고 내 쇼츠와 차별점·개선안을 분석해줘"
> **상태**: 분석 완료 (실측 기반). P1·P3·P4 구현 완료 (2026-07-03). P0(운영)·P2(훅 씬 개편)·P5(운영) 미착수.

### 진단 (내 채널 실측: UCYNNMfkMW_EZJBp514-DjaA, 쇼츠 52편, 2026-07-03 yt-dlp)

1. **업로드 공백 → 배포 붕괴 (가장 치명적)**: 6/18까지 일 1편 유지 시 편당 800~2,700회(최고 7,900회). **6/18→6/29 11일 공백** 직후 360→14→0→0→1회로 붕괴. 쇼츠 시드 테스트(Explore & Exploit)에서 채널이 탈락한 패턴.
2. **제목이 훅이 아닌 주제 요약**: `src/analyzer/political_planner.py:1080` `title=plan.topic` — Stage A가 만든 hook은 제목에 미반영. 잘된 영상 제목은 질문·아이러니형("이름표만 바꾸면 살아날까?"), 망한 영상은 보도자료체("...특검팀 규모와 기간 설명").
3. **나레이션 보도체 고정**: `political_planner_stage_b_prompt.py:90` "tts_text는 보도체 한 문장" → 전 씬 "~라고 밝혔습니다" 나열, 갈등 서사 없음.
4. **훅 씬 = 제목 낭독**: scene 0(3초)이 타이틀 카드 낭독 — 첫 2초 스와이프 방어 실패.
5. **길이 역행**: 잘된 영상 29~44초, 최근 망한 영상 41~56초 (30초 미만 리텐션 임계 ~65%, 30-60초 ~50%).

### 벤치마크 실측 (2026-07-03, 상세는 세션 리서치 보고서)

- 구독자 31만 정치일주(국회 질의 **직캠**) 쇼츠 최고 **500만 뷰**; 구독자 2.4천 민주픽도 30만 뷰 — 쇼츠는 채널 파워보다 클립 훅. TTS 브리핑형(NATV)은 정치 이슈여도 수만 뷰 천장.
- 성공 제목 공식: **"[악역]을 [응징동사]한 [주인공]"** 3단 구조(참교육/사이다/제압/추궁), 실명 1~2개, 의문형·말줄임 클리프행어, 15~30자, #인물명 2~4개. "속보!/충격!"형은 천장 낮음.
- 알고리즘(2025-26): 노출당 시청시간 중심, 첫 1~3초 스와이프율 결정적, 루프형 우대, 일 2~3편 일정 간격 + 평일 20~21시 직후 업로드 권장.
- TTS 쇼츠 조건: 단일 고정 음성(브랜드화), 실클립/모션 배경(정적 슬라이드쇼는 실패 패턴), 자막 필수, 컷 리듬 빠르게.

### 개선안 (우선순위 = 임팩트 × 난이도)

| 순위 | 개선 | 코드 지점 | 난이도 |
|---|---|---|---|
| **P0** | 업로드 리듬 복구: 일 1~3편, 20~21시 직후, 최소 2~3주 무공백 (운영, 코드 무관) | — | 없음 |
| **P1** ✅ | 제목 엔진 교체: `yt_title` 신규 필드(Stage A → `ShortsPlan`). `plan_to_script`에서 `yt_title or topic` 우선. Stage A 프롬프트에 "[악역]-[응징]-[주인공]" / 15~30자 / 실명 규칙 명시. | `political_plan_models.py`, `political_planner_stage_a_prompt.py`, `political_planner.py:1080` | 하 |
| **P2** ✅ | 훅 씬 개편: scene 0 타이틀 카드 낭독 제거 → narrations[0].speaker≠""이면 원본 클립 mute=False + yt_title 자막 오버레이. 폴백(speaker 없음/topic)은 기존 TTS 훅 유지. | `political_planner.py`, `stage_b_prompt`, `generate/route.ts` | 중 |
| **P3** ✅ | 나레이션 탈보도체: "보도체 한 문장" → "대립 서사체 (주장→반박→역공 아크, 다양한 문말 허용)" — STAGE_B_SYSTEM_PROMPT, STAGE_B_TOPIC_SYSTEM_PROMPT, STAGE_B_TOPIC_ECONOMIC_SYSTEM_PROMPT 모두 갱신. | `political_planner_stage_b_prompt.py` | 하 |
| **P4** ✅ | 길이·결말: 나레이션 수 4~7개(22~35초), CTA 2초, 총 40초 캡(기존 60초). 프롬프트 + `plan_to_script` 동시 적용. | `stage_b_prompt`, `political_planner.py` CTA/duration | 하 |
| **P5** | 형식 전환: TTS 브리핑(political_pro)보다 **jpolitics V3 모먼트 직캠** 비중 확대 — 직캠형이 실측상 천장 100배 | 리소스 배분 (기존 파이프라인 존재) | 운영 |

### 검증 계획
- P1~P4 적용 후 2주간 P0 리듬으로 업로드 → 편당 조회수 중앙값(기존 ~1,300) 및 첫 48시간 조회수 비교
- 제목 A/B: 동일 이슈를 topic형 vs hook형 제목으로 비교 업로드

---

## ✅ 완료: 경제쇼츠 지원 (정치쇼츠 V2 파이프라인 확장) — 2026-07-02

> 사용자 요청: "현재 정치쇼츠V2 에서는 정치 이야기를 주로 다루는데 경제쇼츠도 같이 다루고 싶어 기획해줘"
> **상태 (2026-07-02)**: Phase 1~5 전체 구현 완료. 미확정 3항목 모두 권장안(토글/신규 3앵글/차분·분석적)으로 확정.
> 검증: pytest 1399 passed / 0 failed (신규 76개 포함), Next.js build 성공(48/48 페이지), 정치 프롬프트 회귀 스냅샷(바이트 동일) 통과.

### 핵심 판단
파이프라인(주제→3안→스크립트→TTS→뉴스클립→Remotion)은 정치·경제가 동일. 달라지는 건 **프롬프트 페르소나·앵글·가드레일·감정톤**뿐 → 새 병렬 모듈 대신 **`category: "political" | "economic"` 파라미터 관통**(기본 political → 기존 동작 무변경).

### 설계 결정 (권장안)
| 항목 | 권장 | 대안 |
|---|---|---|
| 분기 방식 | `category` 파라미터를 프롬프트·모델·API·UI에 관통 | 별도 `economy_planner` 모듈/탭 |
| UI | 기존 political_pro 탭에 **도메인 토글(정치/경제)** | 경제쇼츠 전용 탭 |
| 경제 앵글 3종 | `wallet_impact`(내 지갑) / `cause_analysis`(원인) / `outlook_action`(전망·대응) | 기존 3앵글 재활용 |
| 경제 톤 기본값 | `차분·분석적` | `분노·격앙` 유지 |
| 감정/그라데이션 | 경제=`relatable`(청록·블루), 정치=기존 `angry`(레드) | 신규 emotion 추가(비권장) |
| 가드레일 | 경제="특정 종목 매수/매도·투자 권유 금지, 수치엔 출처·기준시점 명시" | — |

### 구현 단계 (모두 완료)
- [x] **Phase 1 프롬프트 분기 (핵심)**: `political_planner_stage_a_prompt.py`·`_stage_b_prompt.py`의 `build_*_topic_prompt(..., category="political")` 추가 — `STAGE_A_TOPIC_ECONOMIC_SYSTEM_PROMPT`/`STAGE_B_TOPIC_ECONOMIC_SYSTEM_PROMPT` 신설(페르소나/앵글/가드레일 스왑). category 미지정 호출은 기존 문자열과 바이트 단위로 동일함을 테스트로 고정(회귀 방지).
- [x] **Phase 2 플래너·모델**: `generate_three_plans_from_topic(..., category=...)` → `_generate_three_plans_topic_hybrid`/`_stage_a_topic_gemini`/`_stage_b_topic_claude`까지 관통. `ShortsPlan.category: Category = "political"` frozen 필드(+ `Angle`에 `wallet_impact`/`cause_analysis`/`outlook_action` 3종 추가) + to_dict/from_dict 양방향 + 레거시 plans.json(category 키 없음) 하위호환. `plan_to_script()`가 `plan.category`로 emotion(`angry`↔`relatable`)/gradient(청록·블루) 선택.
- [x] **Phase 3 API·CLI**: `/api/political-pro/plans`(topic 모드) body에 `category` 추가, 미지정 시 political 기본 + 톤 기본값도 도메인별 자동 선택. `/api/generate`는 `plansJson`에 이미 `category`가 실려 있어 **무변경**으로 자동 관통 확인. `src/main.py political-pro --category {political,economic}`. `scripts/render_political_pro_topic.py`는 plans.json에서 category를 그대로 읽어 **무변경**으로 동작 확인.
- [x] **Phase 4 UI**: `app/page.tsx` political_pro 탭 topic 모드에 정치/경제 토글 + 도메인별 톤 옵션(경제: 차분·분석적/위기·경고/공감·연대)·주제 placeholder·투자권유 금지 안내 배너. 탭 라벨 "🏛️ 정치·경제", 추천 카드 "정치·경제 숏츠 자동 생성".
- [x] **Phase 5 테스트**: `tests/test_political_planner_category_prompt.py` 신규(프롬프트 category 분기 + 정치 회귀 바이트 동일), `test_political_plan_models.py`에 category round-trip/화이트리스트/레거시 호환 6건, `test_political_planner.py`에 `plan_to_script` emotion 선택 2건, `test_political_topic_plans.py`에 category 관통 2건 + 기존 mock 2건 시그니처 보정. 전체 pytest 1399 passed / Next.js build 48/48 페이지 / remotion·remotion_v3 tsc 0 errors.

### 영향 파일 (실제 8개 + 테스트 4개)
`political_planner_stage_a_prompt.py`, `political_planner_stage_b_prompt.py`, `political_plan_models.py`, `political_planner.py`, `app/api/political-pro/plans/route.ts`, `src/main.py`, `app/page.tsx` (+ `tests/test_political_planner_category_prompt.py` 신규, `test_political_plan_models.py`/`test_political_planner.py`/`test_political_topic_plans.py` 확장)

### 리스크 (해소 상태)
- ~~MEDIUM: `ShortsPlan` 필드 추가 시 기존 plans.json 역직렬화 하위호환~~ → `category` 키 없는 레거시 JSON도 `"political"` 기본값으로 정상 로드 (테스트로 고정)
- ~~MEDIUM: 정치 프롬프트 회귀~~ → category 미지정 시 바이트 단위 동일 검증 통과
- LOW-MEDIUM: 경제 콘텐츠 **투자권유 법적 가드레일** — 프롬프트에 강제했으나 게시 전 사람 검수는 여전히 필수 (UI 배너로 안내)
- LOW: `relatable` 그라데이션/자막색 경제 톤 — 실제 렌더 샘플로 시각 확인은 다음 세션 과제

### 복잡도: MEDIUM (실측: 계획과 일치)

### 확정된 결정 (미확정 3항목 모두 권장안 채택)
1. UI: **토글** (political_pro 탭 topic 모드 내 도메인 토글)
2. 경제 앵글: **신규 3종** (`wallet_impact`/`cause_analysis`/`outlook_action`)
3. 경제 톤 기본값: **차분·분석적**

### 참고: 2026-07-02 경제 주제 e2e 선행 검증
정치 파이프라인 topic 모드(tone=분노·격앙)로 "고유가지원금·6월 CPI 3.2%" 경제 쇼츠 1건 렌더 성공(55.9s, 12/12 뉴스클립). → 파이프라인 재사용 가능성 입증. 신규 파일: `scripts/render_political_pro_topic.py`(토픽 모드 CLI 렌더 재현). deno 2.9.1 설치(yt-dlp YouTube 추출 안정화).

---

## ✅ 진행 중→완료: 정치쇼츠 V3 — 하이브리드 포맷 (원본 발언 50% + TTS 논평 50%)

> 사용자 요청: "TTS가 말하는 부분보다 첨부할 영상에서 말하는 내용을 직접 넣는 게 호응이 좋은 것 같다. 영상에서 말하는 내용 반 / TTS로 논평 반 이렇게 앞으로 제작하면 좋겠다"
> **확정 사항**: 자막 폰트는 Remotion `SceneText.tsx`(Noto Sans KR)와 통일 — Pillow도 NotoSansCJKkr 사용

### 핵심 설계

| 항목 | V2 (기존) | **V3 (하이브리드)** |
|---|---|---|
| TTS 비중 | ~85% | ~50% |
| 원본 발언 | 마지막 1개 (선택) | 본문에 2~3개 교차 |
| BGM | 전 구간 | 원본 비트 중에는 mute |
| 자막 폰트 | TTS 씬 = Noto Sans KR, 원본 씬 = AppleSDGothic | **모두 Noto Sans KR로 통일** |
| Plan JSON | Narration tuple | HybridBeat tuple (kind="tts"/"original") |

### Phase A — 데이터 모델 ✅ (`src/analyzer/hybrid_plan_models.py`)

`HybridBeat` frozen dataclass: kind ∈ {"tts","original"} + 공통 duration_sec + 분기별 필드.
`HybridShortsPlan` frozen dataclass: hook(TTS) + beats(교차) + cta(TTS) + angle + source_*.

**검증 룰**
- `original` 합산 18~30초 / `tts` 합산 18~30초 (50% ±5초 허용)
- 전체 ≤ 50초 (outro 4초 + 여유)
- 첫·마지막 비트는 반드시 TTS
- 원본 비트 사이에 TTS 비트 필수

### Phase B — Plan 생성 프롬프트 ✅ (2-stage hybrid)

- **Stage A — Gemini** (`hybrid_planner_stage_a_prompt.py`): transcript → 인용가치 있는 원본 후보 4~6개 (`clip_start`, `clip_end`, `raw_text`, `quotability_score`)
- **Stage B — Claude** (`hybrid_planner_stage_b_prompt.py`): HybridShortsPlan 조립 (각 TTS 논평은 바로 직전/직후 원본 비트에 대한 평가)
- 3-plan 오케스트레이터 (`hybrid_planner.py`): `generate_three_hybrid_plans()`

### Phase C — 렌더링 ✅ (`src/video/hybrid_renderer.py`)

TTS 비트 = Gemini Charon per-beat TTS 합성 + 배경 mute. 원본 비트 = ffmpeg 컷(원본 음성 유지) + Pillow PNG 자막 overlay. `render_hybrid_shorts()` 최상위 오케스트레이터 추가. ffmpeg concat 재인코딩으로 codec 통일. 오디오 `loudnorm=I=-16:TP=-1.5:LRA=11`로 레벨 정합.

### Phase D — CLI · 웹 UI ✅

`python3 -m src.main political-pro <url> --hybrid` 플래그 완료. 웹 UI 토글 완료 (2026-07-03):
- `app/api/political-pro/hybrid-plans/route.ts` (신규): YouTube 다운로드 + hybrid 기획안 3개 생성
- `app/components/HybridPlanPicker.tsx` (신규): V3 기획안 표시 (비트 구성·TTS/원본 통계)
- `app/page.tsx`: 🏛️V2일반/📺V3하이브리드 토글 (YouTube 모드 전용) + HybridPlanPicker 표시
- `app/api/generate/route.ts`: `hybridMode=on` 분기 → `render_hybrid_shorts()` 호출 → SSE done

### Phase E — Lock-in + 테스트 ✅

`tests/test_hybrid_plan_models.py`: 51 tests (HybridBeat·HybridShortsPlan·ThreeHybridPlansResult 검증/직렬화). pytest 1458 passed / 0 failed. Next.js build 49/49.

### 위험 등급

| 위험 | 등급 | 완화책 |
|---|---|---|
| 원본 음질 편차 | HIGH | `loudnorm` + `afftdn` 노이즈 게이트 + SNR 필터링 |
| Stage A가 좋은 후보 못 찾음 | HIGH | 후보 <2개면 V2로 자동 fallback (경고 표시) |
| Charon↔원본 톤 단절 | MEDIUM | 비트 경계 50ms `acrossfade` |
| Gemini 자막 보정 비용 | MEDIUM | `data/asr_cache/` 해시 캐시 |
| 50/50 강제로 narrative 어색 | MEDIUM | ±5초 허용 |

### 다음 세션 (E2E 검증)

- 웹 UI 토글 완료 (2026-07-03). 실제 URL로 E2E 샘플 생성 후 품질 확인:
  `python3 -m src.main political-pro <실제 URL> --hybrid --plan-idx 0`

---

---

## ✅ 완료: 029 SFX(씬 전환 효과음) 소프트 비활성화 (2026-06-12)

> 사용자 요청: "씬이 바뀔때마다 효과음 넣는 기능이 있는데 효과음을 아예 빼고 싶어"
> 결정: 소프트 비활성화(코드·에셋·테스트 보존, 자동 할당·렌더만 OFF) — 향후 복구 가능
> 정치 모드(jpolitics V3 / political_pro / 정치쇼츠 V2)는 이미 SFX OFF로 락인되어 있어 영향 없음

### 변경 사항
- **`src/video/renderer.py`** — `render_video()` 진입 직후 `enable_sfx = False; auto_sfx = False` 강제. CLI/API에서 어떤 값을 보내도 SFX는 들어가지 않음. `_strip_scene_effects(drop_sfx=True)`가 모든 씬의 `sfx`를 빈 튜플로 치환.
- **`src/video/remotion/src/ShortsComposition.tsx`** — Per-scene SFX 재생 블록 제거(이중 안전망). `SfxConfig` TS 타입은 보존.
- **`app/api/generate/route.ts`** — `useSfx = false` 고정, 클라이언트 토글 무시.
- **`app/api/rerender/route.ts`** — `safeSfx = false` 고정.
- **`app/page.tsx`** — `sfx` 초기값 `false`, "🔊 효과음" 체크박스 6곳 모두 숨김(주석 처리). state는 FormData 호환을 위해 보존.

### 보존 항목 (재활성화 대비)
- `SfxConfig` dataclass / `Scene.sfx` 필드 (`src/analyzer/script_models.py`)
- `src/video/sfx_matcher.py` (자동 할당 모듈)
- `app/components/SfxPicker.tsx` (수동 선택 UI)
- `data/sfx/` (14개 합성 SFX) + `public/sfx/` (5개 QW-04 프로덕션 SFX + LICENSES.md)
- `tests/test_sfx_matcher.py` (단위 테스트)
- `scripts/generate_sfx.py`

### 복구 방법
1. `src/video/renderer.py`에서 `# SFX globally disabled` 주석 블록 3줄 제거
2. `src/video/remotion/src/ShortsComposition.tsx`의 SFX 주석을 원래 `scriptData.scenes.map(...)` 블록으로 복원 (git log 참조)
3. `app/api/generate/route.ts`와 `app/api/rerender/route.ts`의 `useSfx`/`safeSfx` 강제 라인 원복
4. `app/page.tsx`의 `sfx` 초기값을 `true`로, 6개 체크박스 라벨 복원

---

## 🚧 진행 중: 028 AI 인플루언서 — `influencer` 모드 신설 (2026-06-12)

> 기획 세션: 2026-06-12. 사용자 확정: "higgsfield를 사용하는 방식으로 진행" (fal.ai LoRA 스택 대신 Higgsfield 채택)
> 근거: deep-research 2회 — ① 성공사례·플랫폼정책·수익화 (98개 주장 추출, 정책 6건 공식문서 3-0 확정) ② 프리미엄 캐릭터 일관성 기술 비교

### 콘셉트 (확정)
- **"힙업 루틴 전문 피트니스 + 오피스룩 직장인 일상" 듀얼 콘셉트**, 사실적 여성 AI 캐릭터, 성인 팔로워 타깃
- **SFW 수위 고정** — Instagram 추천 제외(섀도밴)가 **계정 단위**로 작동함이 공식 확인됨(help.instagram.com/313829416281232). 비치는 옷 등 suggestive 판정 요소 금지를 코드 상수로 강제
- 벤치마크: @fit_aitana (6개월 23.6만 팔로워, 월 평균 €3k·피크 €10k, 협찬 ~$1k/포스트 + Fanvue 구독). 전략 핵심 = 백스토리 있는 '인생 서사' 주간 대본화
- 플랫폼: Instagram 주력(수동 업로드) + YouTube Shorts/TikTok 보조(기존 업로더 재사용, AI 라벨 의무 처리)

### 기술 스택 (Higgsfield 단일 플랫폼)
- **캐릭터 고정**: Soul ID 학습 (~$3/회, 15~20장) — LoRA 대체
- **이미지 양산**: Soul 2.0 + Soul ID (패션/일상 프리셋 80+), 편집은 플랫폼 내 Nano Banana Pro
- **영상 i2v**: 허브 내 Seedance 2.0(히어로 씬 — 멀티씬 캐릭터 일관성 1위) / Kling(대량 b-roll — 저단가)
- **통합**: Higgsfield Cloud API (cloud.higgsfield.ai), 폴백 공식 MCP (higgsfield.ai/mcp)
- 비용: 구독 Plus ~$34-49/월 (물량 증가 시 Ultra ~$84-129), Soul ID 학습 $3
- OpenAI 미사용 (기존 방침 유지)

### Phase
- [ ] **Phase 0 — 셋업 + 캐릭터 캐스팅 (코드 최소)**: ① Higgsfield 구독 + Cloud API 키 발급(사용자 작업) + API 커버리지 확인(Soul ID 학습/Soul 2.0/영상이 API로 노출되는지 — 미노출 항목은 웹 UI 1회성 수동 + 생성만 API) ② 캐릭터 설정 문서(이름·백스토리·정체성 앵커 3종: 헤어/시그니처 패션/컬러 + SFW 수위 가이드라인) ③ 후보 시안 3~5종 생성 → 사용자 선택 → Soul ID 학습 → 일관성 실측 ④ 같은 캐릭터 컷으로 Seedance 2.0 vs Kling 영상 실측 비교
- [ ] **Phase 1 — 이미지 파이프라인** (`src/influencer/`): `higgsfield_client.py`(Cloud API), `persona.py`(frozen dataclass, 수위 가드 상수), `content_planner.py`(주간 콘텐츠 캘린더 — Claude, 힙업 루틴 N + 오피스 일상 M + 서사 포스트), CLI `influencer` 서브커맨드
- [ ] **Phase 2 — 영상 파이프라인**: i2v(Seedance 2.0/Kling) + 기존 Remotion 쇼츠 조립 재사용(정지컷 캐러셀 + 5초 모션 b-roll 혼합 포맷 — 운동 시연 양산은 AI 물리 한계로 회피)
- [ ] **Phase 3 — 운영 도구**: 웹 UI 탭, YouTube/TikTok 업로더 연동 + AI 라벨 자동 처리, 자동 업로드 차단 가드(검수 필수, jpolitics 패턴 계승), 3줄 요약+해시태그 규칙 적용

### 리스크
- HIGH: Instagram 계정 단위 추천 제외(공식 확정) → 수위 상수 강제 + 게시 전 검수 게이트
- HIGH: 계정 정지 — AI 라벨 명시에도 셀카 본인인증 단계 영구정지 사례(포럼) → 자연스러운 성장 패턴, 플랫폼별 계정 분리
- MEDIUM: Higgsfield API 커버리지 불확실(Soul ID 학습이 API 미노출 가능성) → Phase 0에서 확인 후 통합 범위 확정
- MEDIUM: 운동 동작 영상 물리 오류(Veo-3 스포츠 성공률 60%, arXiv 2512.14691) → Seedance 우선 + 승인 게이트
- LOW: 크레딧 소진 → Ultra 전환 (Kling 무제한 옵션)

---

## 🚧 진행 중: 027 정치쇼츠 V3 재구축 — "모먼트 직캠" 포맷 (2026-06-11)

> 기획 세션: 2026-06-11. 사용자 확정: "네" (결정사항 1~3 권고안 채택)
> 근거: 벤치마크 실측 분석 — 겸손은힘들다 쇼츠(24만~280만뷰) 2편 프레임 분석, YTN 청문회 모먼트(26만뷰), 국회직캠(구독 207, 중앙값 1,200뷰)과 비교

### 핵심 결정
- **V2(political_pro) 무수정** — 안정 운영, lock-in 유지
- **기존 V3(jpolitics, @김정치입니다 포맷) 전체 삭제** — 6,834줄 (src 2,209 + app 970 + tests 2,541 + remotion_v3 1,114)
- **신규 V3 = 모먼트 직캠 포맷**: ①풀블리드(여백0) ②원본 음성(TTS 제거, --tts-bridge 옵션만) ③질문형 떡밥 훅 타이포 카드(첫 1~2초) ④감정 모먼트 검출(웃음·충돌·언성) ⑤실시간 발언 자막 ⑥질문형 제목+해시태그 설명란 분리
- 격리 원칙 계승: V1/V2 파일 0 수정, read-only import만, page.tsx 버튼 1개
- 데이터: data/jpolitics 산출물 보관 / data/jpolitics_reference 백업 후 삭제
- 기존 V3 lock-in 메모리 7항목 폐기 (출처라벨 하단·효과음0·전환0은 신규에 계승)

### 파이프라인
YouTube URL → 다운로드+transcript(youtube_downloader 재사용) → Gemini 멀티모달 모먼트 검출 톱5 → 사용자 선택 → ffmpeg 컷+9:16 풀블리드 센터크롭(--crop-x 보정) → Remotion: 풀블리드+훅 타이포 카드+실시간 자막+출처 라벨 → 질문형 제목 3안+설명란 해시태그+고정댓글 질문 (업로드 수동)

### Phase
- [x] **Phase 0 (완료 2026-06-11)**: 기존 V3 삭제 (6,834줄 + reference 6.1MB, git 복구 가능), page.tsx 버튼 주석 처리(Phase 4에서 복원), lock-in 메모리 갱신. 회귀: 1283 passed + 빌드 성공
- [x] **Phase 1 (완료 2026-06-11)**: 모먼트 검출 엔진 — `src/jpolitics/` 신규 (models/moment.py, analyzer/moment_detector.py + prompts.py, main.py CLI). 17 신규 테스트, 전체 1300 passed. **실 영상 E2E 검증**: YTN 청문회 영상에서 멀티모달이 웃음 모먼트(22~32s, conf 1.0) 정확 검출 + 질문형 훅 생성 확인. transcript 폴백 체인 동작 확인. Files API 간헐 FAILED 실측 → 2회 재시도 추가. 부수 수정: python-dotenv 미설치로 CLI에서 .env.local 미로딩이던 잠복 버그 해결(requirements.txt 추가)
- [x] **Phase 2 (완료 2026-06-11)**: 클립 가공 — `src/jpolitics/video/clip_maker.py`(ffmpeg 재인코딩 9:16 크롭, ClipResult), `src/jpolitics/video/captions.py`(VTT→transcribe 폴백 체인, 구간 필터·상대화·중복제거). `src/jpolitics/models/clip.py`(CaptionCue+ClipResult frozen dataclass). `cut` CLI 서브커맨드. 27 신규 테스트, 63 jpolitics passed. Next.js 빌드 성공 (tsconfig.json exclude 추가).
- [x] **Phase 3 (완료 2026-06-11)**: Remotion V3 신규 컴포지션 — `src/video/remotion_v3/`(MomentShorts composition, HookCard·LiveCaption·SourceLabel 컴포넌트). `src/jpolitics/video/renderer.py`(render_moment_short). `render`/`run` CLI 서브커맨드. 19 신규 테스트. 전체 63 jpolitics passed + 빌드 성공.
- [x] **Phase 4 (완료 2026-06-11)**: 메타+웹 UI — `src/jpolitics/analyzer/meta_generator.py`(MetaResult: 제목 3안·해시태그·고정댓글, Claude 1-shot), `src/jpolitics/api_bridge.py`(detect/cut/render/meta JSON 어댑터), `app/jpolitics/page.tsx`(5단계 state machine: idle→detecting→moments→processing→done), API 라우트 3개(detect/render/meta SSE), `app/page.tsx` V3 버튼 주석 해제. 31 신규 테스트, 전체 94 jpolitics passed + Next.js 빌드 성공.
- [ ] **Phase 5**: E2E — 실제 영상 1편 생성 + 전체 회귀

### 리스크
- HIGH: 모먼트 검출 품질 — Gemini 멀티모달로 해결, 무료 티어 10 req/day 병목. 폴백: transcript 기반 검출
- MEDIUM: 센터 크롭 화자 잘림 → --crop-x 수동 보정, 얼굴 인식은 후속
- MEDIUM: 원본 음성 저작권 — V2와 동일 수준, 출처 라벨 필수
- LOW: 회귀 — 격리 구조

---

## 이전 계획


## 🚧 진행 중: 026 운영 안정성 + 미완성 기능 정리 (2026-06-11)

> 기획 세션: 2026-06-11 (/plan — 프로젝트 전체 분석 후 개선 로드맵)
> 사용자 확정: "진행" (Phase 1부터, Phase 2B는 UI 토글 숨김 권고안 채택)
>
> **상태 (2026-06-11)**: Phase 1 완료 + Phase 2 항목 4(2B 숨김) 완료.
> - cleanup CLI: `src/maintenance/cleanup.py` + `python3 -m src.main cleanup` (dry-run 기본, 실측 743파일/1.69GB 식별)
> - 업로드 재시도: `src/upload/retry.py`(backoff) + `src/upload/upload_history.py`(이력 JSON) — YouTube/TikTok 연결
> - 브라우저 진단: `src/video_gen/browser_diagnostics.py` — freepik/deevid 실패 시 세션만료/DOM변경/네트워크 구분 메시지
> - Veo 3 토글: `app/page.tsx`에서 숨김 (코드 보존, 주석으로 복원 위치 표기)
> - 검증: pytest 1382 passed/0 failed, 신규 파일 ruff clean, Next.js 빌드 성공
> - 잔여: Phase 2 항목 5(팩트체크 통합)·6(NotebookLM), Phase 3(UI 편의), Phase 4(부채)

### 현황 진단 (탐색 에이전트 2개 분석 결과)

| 영역 | 상태 | 근거 |
|------|------|------|
| Phase 1A/1B/2A (Gemini transcript·분석·이미지) | ✅ 통합 완료 | youtube_downloader.py:352, route.ts:1054 |
| Phase 2B (Veo 3 영상) | ⚠️ 골격만, selector 미검증 | gemini_web_video_gen.py:1-13 "초안" 명시 |
| Phase 3A/3B/4 (멀티보이스·NotebookLM·팩트체크) | ⚠️ 코드만 존재, 호출처 0 | main.py/route.ts에서 미사용 |
| 브라우저 자동화 안정성 | ⚠️ generic 에러, 세션 만료 자동복구 없음 | freepik_gen.py:298-301 |
| 데이터 관리 | ❌ 정리 정책 없음, 6.8GB 누적 | data/political_pro 1.5GB 등 |
| 웹 UI 운영성 | ⚠️ 재시도 버튼·히스토리 목록 없음 | page.tsx:271 에러 시 reset만 |
| 업로드 | ⚠️ 즉시 업로드만, 재시도·예약·이력 없음 | youtube_uploader.py |
| 기술 부채 | main.py 1735줄, bare pass×3, 테스트 공백(editor/upload) | political_planner.py:864-878 |

### Phase 1: 운영 안정성 (이번 세션)
1. **브라우저 자동화 공통 안전장치** — selector 미발견 시 원인 구분 로깅(DOM 변경/세션 만료/네트워크), 공통 헬퍼를 freepik/deevid/gemini generator에 적용. 세션 만료 감지 → 명확한 재로그인 안내.
2. **데이터 정리 CLI** — `python3 -m src.main cleanup [--dry-run]`. temp 24시간, 중간산출물(images/videos/audio) N일 보관, 최종 outputs 보존. dry-run 기본.
3. **업로드 재시도** — YouTube/TikTok 업로드 exponential backoff + 업로드 이력 JSON 기록.

### Phase 2: 미완성 Gemini 기능 정리
4. **Phase 2B (Veo 3)**: UI 토글 숨김 처리 (완성 보류 — gemini.google.com selector 유지보수 부담 HIGH 리스크). 코드는 보존, 추후 완성 결정 시 재노출.
5. **Phase 4 (팩트체크) political_pro 통합**: 기획안 검수 단계에 🟢/🟡/🔴 배지 표시. 정치쇼츠 lock-in 포맷 불변(영상 출력 무변경, 검수 화면에만 추가).
6. **Phase 3B (NotebookLM 스타일)**: 보류 (우선순위 낮음).

### Phase 3: 웹 UI 운영 편의
7. 실패 시 "같은 설정으로 재시도" 버튼 (reviewSnapshot 확장)
8. 프로젝트 히스토리 페이지 (/projects)
9. 진행률 개선 (고정 8단계 → 실제 단계 기반 + 경과 시간)

### Phase 4: 기술 부채 (여유 시)
10. main.py 명령별 모듈 분리, political_planner.py bare pass 로깅, editor/upload 테스트 보강

### 리스크
- HIGH: Phase 2B selector 유지보수 → 숨김으로 회피
- MEDIUM: cleanup CLI 삭제 작업 → dry-run 기본 + outputs 제외
- LOW: 모든 Phase에서 정치쇼츠 V1/V2/V3 lock-in 포맷 불변

---

## 이전 계획

# ContentsMaker 개발 계획 및 진행 상태

> 블라인드 / NATV / 정치 / 셀럽 영상을 YouTube Shorts로 자동 변환하는 파이프라인

**마지막 업데이트**: 2026-06-05

---

## ✅ 완료: 025 정치쇼츠 V3 — "@김정치입니다" 포맷 도입 (2026-06-05)

> 상태: **E2E 4종 레이아웃 시각 검수 PASS** — Phase 1~7 + E2E (T041/T055/T063/T071) + T082 quickstart 검증 완료. 잔존: T074 V1/V2 byte-equality baseline (V1/V2 영상 새로 생성 필요, 옵션).
> 기획 세션: 2026-06-05
> 참고 채널: [@김정치입니다](https://www.youtube.com/@김정치입니다)
> **아키텍처 모드: 완전 격리 (Total Isolation)** — 기존 파일 0 수정 원칙, 단 진입 버튼 1개 예외
>
> **검증 결과 (2026-06-05)**:
> - jpolitics 테스트: 99 passed, 3 skipped (regression baseline 미생성, SKIP OK)
> - V1/V2 회귀 테스트: **1254 passed, 1 skipped** (SC-003 297+ 한참 초과)
> - V1/V2 Remotion tsc: 0 errors (회귀 0건)
> - V3 Remotion tsc: 0 errors
> - Next.js 빌드: 47/47 페이지 컴파일 성공 (`/jpolitics` + 3 API 라우트 포함)
> - 격리 가드: 3/3 통과 (V1/V2 보호 파일 무수정 + read-only import만 + `app/page.tsx` 버튼만 추가)
> - **E2E 4종 레이아웃 (T041/T055/T063/T071)**: 모두 30.06초 영상 시각 검수 PASS
>   - talking_head: 조국 사퇴 영상 (노란 헤드라인 + 자막 + 출처 라벨 3요소)
>   - vs_card: 양향자 vs 추미애 (좌 빨강 국힘 + 우 파랑 더민주 + 인물 사진)
>   - grid_2x2: 평택을 후보 4명 (2×2 그리드 + 인물 사진 + 정당 컬러 테두리)
>   - data_card: 조국 재산 56억 (인물 사진 720×720 + 거대 빨강 "56억 원" 144px)
> - 락인 검증 (T041a): 오디오 트랙 1개 ✓ / 씬 경계 무음 검출 ✓ / clip_search_query 메타 ✓

### 요구사항
YouTube 채널 `@김정치입니다`의 영상 제작 방식을 분석하고, 그 포맷을 자동으로 재현하는 **"정치쇼츠 V3"** 탭을 신설한다. 기존 V1(`political`) / V2(`political_pro`)와 공존, 옵트인 탭.

### 🔒 격리 원칙 (사용자 lock-in)
- **모든 V3 코드는 독립 디렉토리에 격리** — `src/jpolitics/`, `src/video/remotion_v3/`, `app/jpolitics/`, `tests/jpolitics/`
- **기존 파일 편집 0** — 유일한 예외: `app/page.tsx`에 V3 진입 버튼 1개 추가 (사용자 요청)
- **기존 코드는 read-only import만** — `youtube_news_searcher`, `naver_image_search`, `_call_claude`, `gemini_backend` 등 재사용은 import만 (편집 X)
- **회귀 0 보장** — 기존 V1/V2/celebrity/briefing 297+ 테스트 자동 무회귀

### 채널 포맷 분석 결과 (샘플 3편 검증)

| 샘플 | 주제 | 레이아웃 | 데이터 패턴 |
|---|---|---|---|
| **S1** 조국 사퇴 (nPOJYSXdICI) | 1인 연설/인터뷰 | Talking Head (원본 풀스크린) + 페북 글 인서트 | 상단 노란 헤드라인 / 하단 자막 박스 / 출처 라벨 |
| **S2** 양향자 vs 추미애 (fBJH4SX02Ig) | 2인 대결/논평 | VS 카드 (좌·파랑 / 우·빨강 정당 컬러) → Talking Head | 정당 컬러 카드 + MBC 라디오 출처 |
| **S3** 평택을 후보 4명 (_eGbiXgBI6E) | 다인 비교 | 2x2 그리드 (4명 사진) + 시간별 데이터 슬라이드 | 빨강 강조 데이터 (재산/세금/공약) |

### 공통 시각 패턴 (7요소)
1. **고정 헤드라인 (Hook Title)** — 영상 전체 노란 박스 + 검정 두꺼운 한글 폰트 2줄
2. **하단 자막 박스** — 흰 라이트박스 + 실시간 캡션, 빨강 강조 가능
3. ~~채널 워터마크~~ — **본 프로젝트는 제외 (사용자 lock-in)**
4. **출처 라벨** — 하단 "출처 : XXX / YYYY.MM.DD" (외부 인용 시)
5. **레이아웃 다양화** — Talking Head / VS 카드 / 2x2 그리드 / 데이터 슬라이드
6. **정당 컬러 코드** — 민주(파랑) / 국힘(빨강) 정확 매칭
7. **데이터 강조** — 큰 빨간 숫자 (재산/세금/연도 등 비교 수치)

### 사용자 Lock-in 결정 (2026-06-05)
| 항목 | 결정 |
|------|------|
| TTS 보이스 | **V1 락인 유지 — `ko-KR-InJoonNeural` +22%** (Charon 사용 안 함) |
| 채널 워터마크 | **제외** (V3는 워터마크 없음, 출처 라벨만 유지) |
| 레이아웃 범위 | **4종 모두 구현** — `normal` / `vs_card` / `grid_2x2` / `data_card` |
| 효과음(SFX) | **영구 0** — 어떤 씬에도 효과음·BGM 삽입 금지 (FR-034, SC-011) |
| 씬 전환 효과 | **하드 컷만** — 그라데이션·페이드·디졸브 미사용 (FR-035, SC-012) |
| TTS 씬 간 gap | **300 ms 고정** — 그룹 경계에서만 0.3초 무음 (FR-036, SC-013) |
| 영상 추출 흐름 | **Gemini Files API → Claude 검색 키워드 결정 → yt-dlp 다운로드** 3단계 분업 (FR-037, SC-014) |

### V1/V2/V3 차별점

| | V1 (political) | V2 (political_pro) | **V3 (jpolitics)** |
|---|---|---|---|
| 기획 | 1단 Claude 분석 | RTF 6요소 3안 비교 | RTF + **레이아웃 자동 분류** (TH/VS/GRID/DATA) |
| 레이아웃 | 풀스크린 1종 | normal / split 2종 | **normal / vs_card / grid_2x2 / data_card 4종** |
| 자막 | 3줄 (단일색) | 1줄 4색 + emphasis | 1줄 4색 + **고정 헤드라인 노란 박스** |
| 데이터 시각화 | 없음 | 없음 | **인물 카드 + 빨강 강조 수치** |
| TTS | InJoonNeural +22% | Gemini Charon Newscaster | **InJoonNeural +22% (V1 락인 유지)** |
| 출처 라벨 | metadata만 | 하단 letterbox | 하단 letterbox **(워터마크 제외)** |
| 이미지 소스 | 원본 클립 | 원본 클립 | **원본 클립 + Naver 인물 사진 + 정당 로고 자동 페치** |

---

### 구현 단계 (완전 격리 — 10 Phase)

**Phase 1 — Spec 문서 + 샘플 보관 (read-only)**
1. `specs/010-jpolitics-v3-format/{spec,plan,tasks,data-model,research,quickstart}.md` 작성
2. `data/jpolitics_reference/` — 샘플 3편 키프레임 보관 (`/tmp/jpolitics_analysis/`에서 이동)
3. lock-in 항목: TTS=InJoonNeural+22%, 워터마크 없음, 레이아웃 4종, 진입은 메인 페이지 버튼 1개

**Phase 2 — `src/jpolitics/` 패키지 골격 + 독립 모델 (TDD)**
4. `src/jpolitics/__init__.py`, `src/jpolitics/models/__init__.py`
5. `src/jpolitics/models/script.py` — **독립 `JpoliticsScript` / `JpoliticsScene` frozen dataclass**
   - 필드: `id`, `timestamp`, `duration`, `type`, `text`, `voice_text`, `visual_layout` (`normal`/`vs_card`/`grid_2x2`/`data_card`), `subtitle_color`, `subtitle_emphasis`, `headline_pin`, `comparison_cards`, `data_emphasis_color`, `clip_path`, `clip_query`
   - Scene 상속 없음, 완전 독립 클래스
6. `src/jpolitics/models/plan.py` — 독립 `JpoliticsPlan` / `JpoliticsThreePlansResult`
7. 테스트: `tests/jpolitics/test_models.py` — 라운드트립, 카드 1~4개, 4종 layout 검증

**Phase 3 — 인물 카드 페치 모듈 (독립)**
8. `src/jpolitics/scraper/politician_card.py`:
   - `from src.scraper.naver_image_search import search_image` (read-only import)
   - `fetch_politician_card(name) -> dict` — Naver 검색 → 정면 사진 1장 → `data/politician_cards/{name}.json` 캐시
   - `PARTY_COLORS` 상수 (민주 #004EA2 / 국힘 #E61E2B / 조국혁신당 #0073CF / 개혁신당 #FF7920 / 무소속 #888)
   - `infer_party(name)` — Claude 1-shot 추론 (claude_analyzer._call_claude read-only import)
9. 테스트: 캐시 히트/미스, 무소속 회색 폴백, Naver 미발견 폴백

**Phase 4 — Planner (독립 Stage A/B)**
10. `src/jpolitics/analyzer/prompts.py` — `build_stage_a_prompt()`, `build_stage_b_prompt()`
    - Stage A: 영상 분석 + **레이아웃 분류** (`talking_head` / `vs_2way` / `comparison_grid` / `data_comparison`)
    - Stage B: 씬별 `visual_layout` + `comparison_cards` (필요시) + 첫 씬 `headline_pin` (8~14자)
11. `src/jpolitics/analyzer/planner.py`:
    - `from src.analyzer.claude_analyzer import _call_claude` (read-only import)
    - `from src.analyzer.gemini_backend import call_gemini` (read-only import)
    - `generate_three_plans(youtube_url, transcript, ...) -> JpoliticsThreePlansResult`
    - `plan_to_script(plan) -> JpoliticsScript` (카드 씬에 politician_card 페치 + 정당 컬러 주입)
12. 테스트: 4종 레이아웃 분류, 카드 페치 mock, 헤드라인 ≤14자

**Phase 5 — TTS wrapper (V1 락인 하드코딩)**
13. `src/jpolitics/tts/voice.py`:
    - `VOICE = "ko-KR-InJoonNeural"`, `RATE = "+22%"` 모듈 상수 락인
    - `synthesize(script: JpoliticsScript) -> tuple[Path, list[SceneTiming]]` — edge-tts 직접 호출
14. 테스트: 보이스 상수 변경 불가 검증, scene_timings 생성 검증

**Phase 6 — `src/video/remotion_v3/` 독립 Remotion 패키지**
15. 디렉토리 생성 + `package.json` (remotion 의존성만), `tsconfig.json`
16. `src/index.ts` → `registerRoot(Root)`
17. `Root.tsx` — V3 전용 composition 등록 (`<Composition id="JpoliticsShorts" ...>`)
18. `JpoliticsComposition.tsx` — main composition (background + PinnedHeadline + scene routing + outro + audio)
19. 컴포넌트 8종 (모두 신규):
    - `components/PinnedHeadline.tsx` — 영상 전체 상단 노란 박스 + 검정 두꺼운 폰트 2줄
    - `components/TalkingHeadScene.tsx` — 원본 클립 풀스크린
    - `components/VsCardScene.tsx` — 좌·우 분할, 정당 컬러 배경
    - `components/ComparisonGridScene.tsx` — 2x2 그리드 + 데이터 빨강 강조
    - `components/DataCardScene.tsx` — 단일 인물 카드 + 큰 데이터
    - `components/SubtitleBlock.tsx` — V2 자막 패턴 복제 (4색 + emphasis)
    - `components/Background.tsx` — V2 패턴 복제 (그라데이션)
    - `components/Outro.tsx` — V2 패턴 복제
    - `components/LetterboxFrame.tsx` — 하단 출처 라벨 영역
20. 테스트: `npx tsc --noEmit` 통과, preview 4종 스크린샷

**Phase 7 — Python renderer wrapper (독립)**
21. `src/jpolitics/video/renderer.py`:
    - `render(script: JpoliticsScript, audio_path: Path, scene_timings, output_path)` — `npx remotion render` 호출 with `src/video/remotion_v3/`
    - 자산 복사: 클립/오디오/인물 카드 → `src/video/remotion_v3/public/` (격리)
22. 테스트: subprocess mock + 자산 복사 검증

**Phase 8 — CLI entry (독립 모듈)**
23. `src/jpolitics/main.py`:
    - argparse: `python3 -m src.jpolitics.main <youtube_url>` / `--source-type topic --topic "..."`
    - 흐름: transcript → planner → 사용자 선택 (CLI prompt) → tts → renderer
24. 테스트: argparse 분기, e2e (transcript fixture)

**Phase 9 — Next.js 독립 페이지 + API (`app/jpolitics/`)**
25. `app/jpolitics/page.tsx` — V3 전용 페이지 (URL `/jpolitics`)
26. `app/jpolitics/components/JpoliticsPlanPicker.tsx`, `JpoliticsScriptReviewer.tsx`
27. `app/jpolitics/api/plans/route.ts` — V2 패턴 복제, jpolitics_main 호출
28. `app/jpolitics/api/render/route.ts` — V2 패턴 복제
29. **FR-020 업로드 차단 + FR-021 검수 필수 배너** (rose-amber)
30. 테스트: API smoke + 3줄 요약 + 해시태그

**Phase 10 — 진입 버튼 + E2E 검증 + lock-in (유일한 예외 수정)**
31. ⚠️ **유일한 기존 파일 수정**: `app/page.tsx` 헤더 영역에 V3 진입 버튼 1개 추가
    - 예: `<button onClick={() => router.push("/jpolitics")}>🟡 정치 V3</button>`
    - 기존 8개 탭 union 타입·로직·폼 모두 무수정 — 헤더 버튼만 추가
32. 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성
33. 회귀 검증: 기존 297+ 테스트 무회귀 + 신규 50+ 통과 + Next.js 빌드 + `cd remotion_v3 && npx tsc --noEmit`
34. 3줄 요약 + 해시태그 자동 첨부 검증

---

### 영향 받는 파일 (격리 모드)

**🆕 신규 파일만** (편집 0):
```
src/jpolitics/                       (Python 패키지 신규 ~12 파일)
  __init__.py, main.py
  models/{__init__,script,plan}.py
  scraper/{__init__,politician_card}.py
  analyzer/{__init__,prompts,planner}.py
  tts/{__init__,voice}.py
  video/{__init__,renderer}.py

src/video/remotion_v3/               (독립 Remotion 패키지 신규 ~12 파일)
  package.json, tsconfig.json
  src/index.ts, Root.tsx, JpoliticsComposition.tsx
  src/components/{PinnedHeadline,TalkingHeadScene,VsCardScene,
                  ComparisonGridScene,DataCardScene,SubtitleBlock,
                  Background,Outro,LetterboxFrame}.tsx

app/jpolitics/                       (Next.js 라우트 신규 ~5 파일)
  page.tsx
  components/{JpoliticsPlanPicker,JpoliticsScriptReviewer}.tsx
  api/plans/route.ts
  api/render/route.ts

tests/jpolitics/                     (격리 테스트 신규 ~6 파일)
  test_models.py, test_planner.py, test_politician_card.py,
  test_tts_voice_lockin.py, test_renderer.py, test_e2e.py

specs/010-jpolitics-v3-format/       (사양 문서 6 파일)

data/jpolitics_reference/            (샘플 키프레임)
data/politician_cards/               (인물 카드 캐시)
data/jpolitics/                      (V3 영상 출력 격리 디렉토리)
```

**🔧 기존 파일 수정** (1개만):
- `app/page.tsx` — **V3 진입 버튼 1개 추가** (헤더 영역, 기존 탭 로직 무수정)

**📖 기존 파일 read-only import** (편집 0):
- `src/scraper/youtube_news_searcher.py` — yt-dlp 검색·9:16 컷 재사용
- `src/scraper/naver_image_search.py` — Naver 이미지 검색 재사용
- `src/analyzer/claude_analyzer.py` — `_call_claude` 재사용
- `src/analyzer/gemini_backend.py` — Stage A Gemini 호출 재사용

---

### 의존성 / 사전 조건
- ✅ `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` (셀럽 모드용 이미 존재) — 인물 사진 검색에 재사용
- ✅ `MS-Hannah-NotoSans-Bold` / `Noto Sans KR Black` — 노란 헤드라인용 (Remotion 이미 설치됨)
- ✅ `data/jpolitics_reference/` — 샘플 키프레임 보관 (lock-in 확인용)
- ❌ ~~채널 워터마크 PNG~~ — **사용자 lock-in: 제외**

---

### 리스크

| 등급 | 항목 | 완화책 |
|---|---|---|
| 🔴 **HIGH** | **저작권** — 정치인 사진(Naver)·뉴스 클립 인용 = 제3자 저작물 | V2와 동일: 업로드 UI 차단(FR-020) + "검수 필수" 배너(FR-021), 보도·논평 목적 명시 |
| 🟡 **MED** | **레이아웃 오분류** — LLM이 talking_head를 grid로 잘못 분류 시 부자연 | Stage A 프롬프트에 4종 명확 예시 + 사용자 수정 가능 UI (선택 드롭다운) |
| 🟡 **MED** | **카드 데이터 환각** — Claude가 "127억" 같은 데이터를 LLM hallucination 출력 | data_card 씬은 transcript에 명시된 숫자만 인용 + 출처 라벨 강제 |
| 🟢 **LOW** | **정당 매핑 누락** — 무소속/신생 정당 헥스 컬러 미정 | `infer_party` 폴백 시 회색(#888) + 경고 로그 |
| 🟢 **LOW** | **Naver 사진 누락** — 인물명 검색 실패 | 그라데이션 폴백 + 콘솔 경고 |

---

### 비용·복잡도 (격리 모드)
- **변동비**: $0 (Naver 무료 25,000건/일, Gemini 무료 250req/일, Edge TTS 무료, Claude 기존 한도)
- **복잡도**: **HIGH (격리 모드 +5h)**
  - Phase 1 Spec: 1-2h
  - Phase 2-5 백엔드 독립 패키지: 8-10h
  - Phase 6 Remotion V3 독립 패키지 (컴포넌트 8종 + 공통 복제): 6-8h
  - Phase 7-9 Renderer + CLI + Next.js: 4-5h
  - Phase 10 진입 버튼 + E2E: 2-3h
  - TDD 테스트: 4-5h
  - **합계: 25-33h** (vs. 통합 안 18-23h, 격리 모드 +7-10h 트레이드오프)
- **신규 LOC**: ~2500 (Remotion 컴포넌트 복제분 ~1000 포함)
- **격리 가치**: 기존 297+ 테스트 자동 무회귀 + V1/V2 락인 100% 보장

---

### 검증 기준 (DoD)
- [ ] 4종 레이아웃(`normal`/`vs_card`/`grid_2x2`/`data_card`) 각각 샘플 영상 1편씩 생성 → 사용자 OK
- [ ] 고정 헤드라인 + 출처 라벨 2요소 모든 씬 노출 확인 (워터마크 제외)
- [ ] TTS = InJoonNeural +22% 하드코딩 검증 (변경 시도 시 테스트 실패)
- [ ] 단위 테스트 신규 50+ 통과 / 회귀 테스트 297+ 유지 (격리로 자동 보장)
- [ ] Next.js 빌드 success + V3 TypeScript `cd src/video/remotion_v3 && npx tsc --noEmit` 통과
- [ ] 기존 V1/V2 Remotion 빌드도 무회귀 (`cd src/video/remotion && npx tsc --noEmit`)
- [ ] 메인 페이지 V3 진입 버튼 동작 + `/jpolitics` 라우팅 확인
- [ ] 기존 V1/V2/celebrity/briefing 탭 무회귀 (탭 union 타입 무수정)
- [ ] 3줄 요약 + 해시태그 자동 첨부

---

### 참고 코드 위치 (read-only 참고용 — 편집 X)
- V2 layout split 패턴 참고: `src/analyzer/script_models.py:135-142` (필드 구조만 참조하여 JpoliticsScene 독립 작성)
- V2 SplitScreenScene 참고: `src/video/remotion/src/components/SplitScreenScene.tsx` (분할 화면 로직 참조)
- 정치_pro Stage A/B 흐름 참고: `src/analyzer/political_planner.py` (병렬 패턴 모방, import는 `_call_claude`만)
- TTS edge-tts 호출 패턴: `src/tts/edge_tts_synth.py` (구현 패턴 참조)
- Naver 이미지 검색 import: `from src.scraper.naver_image_search import search_image`
- Remotion 자산 복사 패턴: `src/video/renderer.py` (격리된 `remotion_v3/public/`로 동일 패턴 적용)
- V2 API route 구조 참고: `app/api/political-pro/plans/route.ts` (구조만 참조하여 독립 작성)
- V2 자막 분할 알고리즘: `src/editor/subtitle_split.py` (read-only import 가능, 자막 품질 동일 유지)

---

## ✅ 완료: 024 유명인 쇼츠 — 유튜브 클립 소스 추가 (2026-05-28)

> 상태: **구현 완료** (커밋: dcb20ea)
> 기획 세션: 2026-05-28 | 구현 세션: 2026-05-28

### 요구사항
유명인 쇼츠에서, 정치 topic 모드처럼 **유튜브에서 해당 인물의 실제 영상을 씬별로 검색·다운로드·9:16 컷**하여 씬 배경 영상으로 쓰는 새 옵션을 추가한다. 기존 동작(Freepik 이미지→영상 / 이미지)은 그대로 유지하고 **옵트인**으로 붙인다.

### 확정된 설계 결정 (사용자 합의)
| 항목 | 결정 |
|------|------|
| 검색어 소스 | **새 `clip_query` LLM 필드** — celebrity 프롬프트가 씬별 영상 검색어 출력("손흥민 골 장면" 등), 미출력 시 `{name} {image_query}` → `{name}` 폴백 |
| 다운로드 | **씬별 ytsearch1** — `youtube_news_searcher.build_scene_clips()` 그대로 재사용 (새 스크래핑 코드 없음) |
| 9:16 처리 | **crop·letterbox 둘 다 구현** → 동일 씬으로 샘플 2종 생성 → 사용자가 보고 lock-in (미정) |
| 기본 동작 | **새 옵션 옵트인** (`--video-source youtube`), 기본값은 현행 유지 |

### 핵심 인사이트
`src/scraper/youtube_news_searcher.py`의 검색·다운로드·컷 로직(`build_scene_clips`, `cut_scene_clip`, `search_and_download_news_clips`)이 **완전히 재사용 가능**. 새 다운로드 코드 0. 작업 본질 = "유명인 파이프라인에 클립 소스 분기 + 씬별 검색어 1필드 + UI 토글".

### 구현 단계

**Phase 1 — 데이터 모델 + 컷 모드 (TDD)**
1. `Scene`에 `clip_query: str | None = None` 추가 (`src/analyzer/script_models.py`) — `to_dict`/`from_dict` 직렬화(값 있을 때만, camelCase `clipQuery` 호환), `image_query`와 동일 패턴
2. `cut_scene_clip()`에 letterbox 모드 추가 (`src/scraper/youtube_news_searcher.py`): `crop_9x16: bool` → `crop_mode: Literal["crop","letterbox"]` (기본 `"crop"`, 하위호환). letterbox vf = `scale=1080:-2,pad=1080:1920:0:(1920-ih)/2:color=black`. `build_scene_clips()`에 `crop_mode` 전달
3. 테스트: `clip_query` 라운드트립, `cut_scene_clip` letterbox vf 인자 생성(ffmpeg mock)

**Phase 2 — 유명인 유튜브 클립 헬퍼 (TDD)**
4. `_build_celebrity_clip_keywords(name, script)` (`src/main.py`): 씬별 검색어. 우선순위 `scene.clip_query` → `f"{name} {scene.image_query}"` → `f"{name}"`. `safe_search_keyword()`로 정리
5. `_run_celebrity_youtube_clips(name, script, *, scene_timings=None, crop_mode="crop")`: scene_durations = timing 있으면 timing 기반 else `scene.duration`. `build_scene_clips()` → `data/videos/celebrity/{ts}_{name}/`. 결과 `[{scene_id, video_path}]` 매핑(None 스킵)
6. 테스트: 검색어 빌더 폴백 체인, scene_id 매핑/None 처리(`build_scene_clips` mock)

**Phase 3 — CLI 배선**
7. `cmd_celebrity` 분기 (`src/main.py`): 새 인자 `--video-source {freepik,youtube}`(기본 freepik), `--clip-crop {crop,letterbox}`(기본 crop). `video-source=youtube`면 Step 5(TTS) 먼저 → scene_timings로 클립 컷 → render(정치_pro와 동일 순서, 싱크 정확). `metadata.source_label` 미설정 시 `"출처: YouTube"` 주입(하단 라벨 시스템 재사용)
8. 테스트: argparse 파싱 + 분기 선택

**Phase 4 — UI / API 배선**
9. celebrity 탭 토글 (`app/page.tsx`): 영상 소스 `이미지 / Freepik 영상 / 유튜브 클립` + crop 옵션
10. `app/api/generate/route.ts`: `celebrityVideoSource`/`celebrityClipCrop` → `--video-source`/`--clip-crop`
11. `app/api/celebrity-rerender/route.ts`: 동일 옵션

**Phase 5 — 샘플 검증 + lock-in**
12. 같은 인물로 crop/letterbox 샘플 2편 생성 → 비교 → 확정안 lock-in (메모리 기록)
13. 3줄 요약 + 해시태그 동반 제공 (고정 룰)

---

## ✅ 완료: 023 정치쇼츠 V2 — 주제 입력 모드 추가 (2026-05-26)

(상세는 prompt_plan.md.bak3 참조)

---

## 이전 계획

(이전 prompt_plan.md는 prompt_plan.md.bak3에 보관)
