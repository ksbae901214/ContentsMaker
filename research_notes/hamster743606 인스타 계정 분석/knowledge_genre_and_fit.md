# @hamster.743606 재분석: 한국어 "지식 스토리텔링" 릴스의 장르 맥락과 ContentsMaker 적합성

> 작성일 2026-10-14. 기존 `genre_and_pipeline_fit.md`를 **대체**하는 노트다. 직접 관측 결과는 `account_catalog.md`(12편 실측)를 따른다.
> 웹 페이지 본문 fetch 도구(jina-reader / fetch MCP)가 이 세션에 없었다. 사용자 규칙에 따라 WebFetch는 쓰지 않았다. 그래서 외부 근거는 **WebSearch 결과 스니펫 수준**이다. 원문 문구 확인이 필요한 항목은 Gaps에 따로 적었다.
> 레포 근거는 파일을 직접 읽고 줄 번호를 확인했다(2026-10-14, 브랜치 `feat/038-upload-package-automation` 작업 트리 기준).

## 0. 이전 노트(genre_and_pipeline_fit.md) 정정 사항

### Takeaway
이전 노트는 계정을 "김햄찌형 AI 햄스터 캐릭터 스킷"으로 **잘못 가정**했다. 그 결과 장르(§1), 제작 기법(§2), 파이프라인 결핍 분석(§4), 채널 전략(§5)의 근거가 대부분 틀렸다. 플랫폼 정책 사실관계(§3)와 레포 파일 지도 일부는 여전히 유효하다.

### Cited Findings
- 실제 포맷은 다음과 같다: 크림 배경, 상단 굵은 제목, 중앙 빈티지 판화풍 일러스트 1장(120초 영상에 8장, 장당 13~22초), 하단 2~3줄 자막, 존댓말 + 게임·자동차 비유 드립 나레이션, 99~170초(중앙값 126.4초). 주제는 (A) 논문 1편 + `출처 :` 표기와 (B) 동물·취미·사물 드립 두 갈래다. — `account_catalog.md` §2·§3 ([Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/))
- 이전 노트의 "AI slop 캐릭터 스킷 / I2V(Kling) / 립싱크 / 캐릭터 시트 일관성 / SFX" 논의는 이 계정에 **해당하지 않는다**. 영상 생성(I2V)이 없다. 정지 일러스트 + 줌/컷 구조이고 캐릭터도 없다. — `account_catalog.md` §2
- 계정명의 "햄스터"는 운영자 닉네임이다("made by 햄스터" 워터마크). 바이오는 "낮엔 전략 기획, 밤엔 앱 개발 / 신기한 동물·생물·물리 이야기"다. — [Instagram 프로필](https://www.instagram.com/hamster.743606/)

### 유지되는 이전 노트 내용 (재검증 범위)
- YouTube 2025-07-15 "불성실한 콘텐츠" 개정과 그 예시 목록 → 유지. 다만 이 포맷과 관련된 예시는 "캐릭터 반복"이 아니라 **"이미지 슬라이드쇼·자동 낭독"** 쪽이다(§4에서 재해석).
- YouTube 합성 콘텐츠 공개 의무는 사실적 콘텐츠에만 적용되고, 한국 AI 기본법(2026-01-22) 표시 의무는 서비스 사업자에게 있다 → 유지.
- 레포 지도 중 `shorts_format.FormatRules`, `voice_config.DARK_BGM_SOURCE_TYPES`, 업로드 패키지·게이트가 정치 전제라는 점 → 유지.
- **폐기**: 캐릭터 일관성(레퍼런스) 결핍, 립싱크 결핍, SFX 재활성화 필요성, `character_skit` source_type 제안, "AI 햄스터 + 정치 = AI 페르소나 조항" 논리. 이 포맷에는 페르소나가 없다. 단, 정치 소재를 섞으면 다른 각도의 리스크가 생긴다(§6).

### Inferences
- 이전 노트의 오류는 브라우저 연결 실패로 실물을 보지 못한 상태에서 핸들 이름("hamster")으로 장르를 추정했기 때문이다. 이 노트의 장르 판단은 실제 프레임과 전사 기반이다.

### Gaps
- 없음(정정 범위는 실측으로 확정).

## 1. 장르 정의와 비교 계정·채널, 2025~2026 트렌드

### Takeaway
이 포맷은 한국에서 "**지식튜브 / 잡학·상식 / 지식 스토리텔링**"으로 불리는 교양 콘텐츠를 **릴스 길이(2분)**로 압축하고 **얼굴 없는(faceless) 일러스트 + 보이스오버** 문법으로 만든 것이다. 롱폼 쪽(사물궁이 156만, 사피엔스 스튜디오 77만)과 1분 숏폼 쪽(지식코리야, 1분과학)은 검증된 시장이다. 반면 "**논문 1편을 썰로 풀고 출처를 다는**" 2분 릴스는 정확히 같은 형태의 대형 사례를 찾지 못했다. 빈 자리일 수도 있고, 검증되지 않은 자리일 수도 있다.

### Cited Findings
**국내 장르 명칭·규모**
- 언론은 잡학·상식을 나누는 유튜브를 '지식튜브'로 부른다. 법·의학 같은 전문 지식이나 역사·철학·미술처럼 거리감 있는 분야를 풀어 설명한다. 사례는 사피엔스 스튜디오(tvN 제작진, 구독 77만), 김성회의 G식백과(65만), 아이템의 인벤토리(48만), 빅쇼트(18만) — [더팩트 '인플루언서 프리즘'](https://news.tf.co.kr/read/ogmeta/1874011.htm)
- 같은 연재에 "교과서 밖으로 나온 역사…'지식 스토리텔링' 콘텐츠 부상" 기사가 있다(제목만 확인, 본문 미확인) — [더팩트](https://news.tf.co.kr/read/ogmeta/2252973.htm)
- 사물궁이 잡학지식: 2018-09-26 개설, 구독 156만, 영상 505개. "사소해서 물어보지 못했지만 궁금했던 이야기", 과학·잡학 위주, "대한민국 최대 과학 유튜브 채널"로 소개된다. 애니메이션 일러스트 + 나레이션 형식이다 — [vidIQ 채널 통계](https://vidiq.com/youtube-stats/channel/UC7F6UDq3gykPZHWRhrj_BDw)(검색 요약)
- 지식코리야: '인간이 고래에게 먹히면' 같은 가정형 과학 쇼츠로 2023년 11월 말 구독 1만 → 두 달 만에 54만. 1분과학은 구독 70만, 누적 6천만 회 — [캐릿](https://www.careet.net/1294)

**해외 대형 사례 (faceless 지식 쇼츠)**
- Zack D. Films: 구독 2,780만, 누적 718억 뷰, 영상당 평균 2,000만 뷰의 3D 애니 호기심 쇼츠. 애니메이터 50명 이상, 공개 구인 기준 편당 $1,000 × 주 40편. 최대 히트작은 31초 2억 5,300만 뷰이고, "질문을 즉시 던지고 답하는 순간 끝낸다" — [OutlierKit 채널 분석](https://outlierkit.com/channel/zackdfilms), [Daniel Rusnok 분석](https://danielrusnok.substack.com/p/how-a-faceless-channel-engineered) (2차 분석, 수익 추정은 신뢰도 낮음)
- "빈티지 미감 역사 팩트 릴스"는 AI 영상 툴 업체가 별도 튜토리얼을 낼 만큼 정형화된 하위 장르다 — [invideo 블로그](https://info.invideo.io/blog/best-ai-vintage-aesthetic-history-reels) (업체 홍보물)

**플랫폼 길이 트렌드**
- Instagram은 2025년 1월 Mosseri 발표로 릴스 상한을 90초에서 3분으로 늘렸다("90 seconds is just too short… we're upping that limit to three minutes") — [Buffer](https://buffer.com/resources/instagram-reels-length), [Deccan Herald](https://www.deccanherald.com/amp/story/technology/instagram-extends-reels-duration-from-90-seconds-to-3-minutes-3363553)
- 길이와 성과의 관계: "90초~3분 릴스는 도달이 약간 낮지만 충성 팔로워의 시청 시간이 강하다", "90초 초과는 알고리즘 도달 감소 위험" — [Castmagic](https://www.castmagic.io/post/how-long-can-an-instagram-reel-be), [Buffer](https://buffer.com/resources/instagram-reels-length) (마케팅 블로그 주장이며 1차 데이터 아님)
- Mosseri가 확인한 핵심 신호는 시청 시간, 도달 대비 좋아요, **도달 대비 DM 공유(sends)**다. Instagram은 시청 비율과 총 시청 초를 함께 본다(1분 영상의 10초와 10초 영상의 10초를 같은 무게로 본다는 설명) — [Lindsey Gamble](https://lindseygamble.com/blog/instagram-reveals-how-its-algorithm-weighs-watch-time-for-reels), [PostEverywhere](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works)
- 2026년 기준 "릴스는 최대 20분까지 가능, 발견(discovery)은 여전히 짧은 쪽이 유리"라는 정리가 있다 — [PostEverywhere](https://posteverywhere.ai/blog/how-the-instagram-algorithm-works) (공식 출처 미확인)
- 한국 정리 글: 2025~2026 인스타 알고리즘은 '저장 및 공유 중심의 가치 평가형 구조'로 전환됐다 — [wikidocs knarchive](https://wikidocs.net/blog/@knarchive/16646/) (2차 정리)
- YouTube Shorts는 2024-10-15부터 3분까지 Shorts로 분류되고 Shorts 수익 배분 대상이다. 단, 롤아웃 초기에는 1분 초과 Shorts가 Shorts 피드 트래픽을 받지 못할 수 있다고 안내했다 — [YouTube 고객센터](https://support.google.com/youtube/answer/15424877?hl=en-GB), [Tubefilter](https://www.tubefilter.com/2024/10/03/youtube-shorts-three-minutes-max-length-redesign-trends-templates/)

### Inferences
- @hamster.743606의 위치(추정): 롱폼 지식튜브의 **서사 밀도**(인물·일화·반전, 예: 베이즈 편의 "위스키 베팅 → 220m")와 숏폼의 **드립 화법**을 결합했다. 길이는 Instagram의 3분 상한을 활용한 2분이다. Zack D. Films식 "30초 질문-답"과 정반대 길이 전략이다.
- 이 계정의 신호(좋아요율 1.8~5.9%, 논문형 좋아요 중앙 643 vs 드립형 260)는 Mosseri의 "총 시청 초 + 공유" 신호와 맞는다. 2분 논문 썰은 끝까지 보면 시청 초가 길고 "이거 봐" 공유 동기가 있는 유형이다. 다만 조회수가 없어 검증하지 못했다.
- 2분 길이는 **YouTube Shorts로도 올릴 수 있다**(3분 이하). 그러나 이 사용자의 채널 실측은 38~62초를 최적으로 잡고 있다(035, 아래 §5). 2분 Shorts 성과는 미검증이다.

### Gaps
- "논문 1편 썰 + 출처 표기" 형태의 한국 인스타 계정을 규모와 함께 찾지 못했다(검색 색인에 소형 인스타 계정이 거의 잡히지 않음). 경쟁 밀도는 미상이다.
- 2분 릴스와 60초 미만 릴스의 도달·완주율을 비교한 **1차 데이터(Meta 공식 또는 대규모 표본 연구)**는 찾지 못했다. 위 수치는 전부 마케팅 블로그의 주장이다.
- 2025~2026 한국 언론이 "논문 썰 숏폼"을 트렌드로 다룬 기사는 찾지 못했다.

## 2. 제작 기법: 일러스트, 보이스, 대본 소싱, 예약 업로드

### Takeaway
이 포맷의 제작 단위는 "**대본 1개 → 세그먼트 6~8개 → 세그먼트당 일러스트 1장 + 나레이션 문장 묶음**"이다. 영상 생성이 필요 없어 기술 난도는 낮다. 품질을 가르는 요소는 ① 일러스트 화풍 고정(스타일 키워드 반복 + 레퍼런스), ② 한국어 구어 드립을 소화하는 TTS(또는 사람 녹음), ③ **논문 요약의 과일반화 통제**다.

### Cited Findings
**빈티지 판화·과학 도판 일러스트**
- 판화풍 세트를 일관되게 만드는 방법: "fine engraving cross-hatch shading, ink linework, ink-and-wash depth, aged sepia paper tone" 같은 기술 키워드를 **모든 장에 똑같이 반복**하거나 Style Transfer로 선 굵기를 고정한다. 빈티지 도판의 4요소는 판화·크로스해칭 선, 잉크 워시 음영, 세피아·종이 톤, 고전적 구도다. 과학 도판(naturalist study plate)은 "black on cream, 하단 캡션 여백" 구성이다 — [Morphic: Victorian engraving](https://morphic.com/resources/images/victorian-engraving-image), [Morphic: vintage book illustration](https://morphic.com/resources/images/vintage-book-illustration-ai) (툴 업체 가이드)
- Midjourney 쪽은 `--sref` 스타일 코드 모음으로 화풍을 고정하는 관행이 있다 — [Patreon: SREF 모음](https://www.patreon.com/posts/142737791) (검색 요약)
- 관측: 대상 계정의 일러스트는 "흰/크림 배경에 소재 하나를 컷아웃한 판화풍, 제한된 팔레트"다 — `account_catalog.md` §2

**한국어 보이스오버**
- 타입캐스트: 700개 이상의 AI 보이스, 문맥 기반 감정 자동 조절, 영상 워크플로 통합을 내세운다. ElevenLabs: 최저 유료 플랜 월 $5에 90분이지만 "한국어 발음이 완벽하지 못하다". 네이버 클로바더빙: 한국어 발음 정밀도가 높지만 무료 사용 시 출처 표기 의무가 있다 — [Dropshot 비교](https://match.dropshot.io/blog/ai-더빙이-처음이라면-나에게-맞는-tts-사이트-4-8708), [타입캐스트 비교 글](https://typecast.ai/kr/learn/tts-natural-pronunciation-comparison-2026/) (후자는 이해당사자 자사 글)
- Gemini TTS: 요청당 입력 최대 5,000자, 짧은 스니펫부터 장문 내레이션까지 지원, 스타일·속도·톤·감정을 자연어로 제어 — [Google Cloud Gemini-TTS 문서](https://cloud.google.com/text-to-speech/docs/gemini-tts)
- 슈퍼톤(Supertone)의 2025~2026 한국어 TTS 비교 자료는 검색에서 확인하지 못했다.

**대본 소싱(논문 → 썰)**
- Peters & Chin-Yee(2025, Royal Society Open Science)는 LLM 10종의 과학 요약 4,900건을 원문과 비교했다. 대부분의 모델이 원문보다 **넓게 일반화**했고(DeepSeek·GPT-4o·LLaMA 3.3 70B는 26~73%), LLM 요약은 사람 요약보다 과일반화 가능성이 약 5배 높았다. "정확하게 하라"고 지시하면 오히려 약 2배 더 과일반화했고, 최신 모델일수록 더 나빴다 — [PMC 원문](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12042776/), [PsyPost](https://www.psypost.org/ai-chatbots-often-misrepresent-scientific-studies-and-newer-models-may-be-worse)

**예약 업로드 (하루 4~5편 정시)**
- Instagram 앱 자체 예약: 하루 최대 25개, 30일 앞까지. Meta Business Suite(데스크톱)로 릴스 예약 가능. 대량 일괄 업로드는 불가하고 앱 전용 음악은 넣을 수 없다 — [SocialPilot](https://www.socialpilot.co/blog/schedule-instagram-reels), [RecurPost](https://recurpost.com/blog/schedule-instagram-reels-with-meta-business-suite). 예약 가능 기간(29일 vs 75일)과 MBS 예약 영상 길이 상한(90초라는 서술)은 출처끼리 **충돌**하며, 90초 서술은 3분 확대 전 정보로 보인다.
- Instagram Graph API 콘텐츠 게시: 계정당 24시간 롤링 50건 한도(`content_publishing_limit` 엔드포인트로 확인). 2023-07-01 이후 API로 올린 단일 피드 영상은 전부 릴스로 게시된다 — [Meta 개발자 문서](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing)

### Inferences
- 대상 계정의 "07:06 / 11:06 / 15:07 / 18:07 / 21:07" 분 단위 정시성(`account_catalog.md` §4)은 앱/MBS 예약이나 API 예약의 전형적 흔적이다. 하루 4~5편은 두 한도 모두에 한참 못 미친다. 운영자가 "앱 개발자"라고 자기소개한 점을 보면 API 자동화 가능성도 있다(미확인).
- 나레이션이 문장 사이 무음 없이 균일하다는 실측(-40dB 이하 0.3초 이상 7회/120초)은 TTS 합성 또는 강하게 편집한 녹음과 맞는다. 판별은 불가하다(추정).
- 레포의 Gemini TTS 경로는 **대본 전체를 1회 호출**로 합성한다(`src/tts/gemini_tts_generator.py` l.1~10, l.240~251). 2분 대본은 1.0배속 기준 약 930자(126초 × 7.4자/초, `political_length` 보정치)로 5,000자 한도 안이다. 하루 4편이면 무료 일일 한도(메모리 기준 약 10회)의 절반 가까이를 쓴다. 재렌더 여유가 적다.
- 과일반화 연구는 이 포맷의 핵심 리스크를 정면으로 겨냥한다. "논문 PDF → LLM 요약 → 썰"을 자동화하면 "쥐 실험 → 사람에게도", "상관 → 인과" 류 오류가 체계적으로 들어간다. **원문 초록·결론 문장 대조 체크를 사람이 하거나 게이트로 강제**해야 한다.

### Gaps
- 대상 계정이 실제로 쓰는 이미지 툴·TTS·예약 수단은 확인하지 못했다(메타데이터에 흔적 없음, `music_info:null`만 확인).
- Freepik의 Nano Banana Pro / Gemini Imagen 4로 판화풍 세트를 냈을 때 일관성이 어떤지는 실험하지 않았다.
- 타입캐스트·클로바더빙의 **상업적 이용(수익화 채널) 라이선스 조건**은 원문을 확인하지 못했다.

## 3. 정책·리스크: YouTube 불성실 콘텐츠, AI 라벨, 저작권, 정확성

### Takeaway
이 포맷의 YouTube 리스크는 이전 노트가 지적한 "캐릭터 반복"이 아니다. 정책 예시 문구 **"이미지 슬라이드쇼 / 자동 낭독 / 같은 내레이션 구조의 슬라이드쇼"**와 겉모양이 겹친다는 점이다. 이를 상쇄하는 것은 **편마다 다른 소재·고유 해석(드립, 비유)·출처 명시**다. AI 라벨은 비사실적 일러스트라면 Meta·TikTok·YouTube 모두 의무 대상 밖일 가능성이 높다. 남은 회색지대는 사람처럼 들리는 TTS 음성이다. 저작권상 논문의 사실·아이디어는 자유롭게 쓸 수 있지만 **논문의 그림(figure)과 문장은 보호된다**.

### Cited Findings
**YouTube (2025-07-15 개정, 2026-01 집행 강화)**
- 2025년 7월 '반복 콘텐츠'를 '불성실한 콘텐츠'로 개명했고, 2026년 1월 대규모 집행 캠페인으로 다수 채널의 수익화가 해제됐다는 정리가 있다 — [AIR Media-Tech 타임라인](https://air.io/en/monetization/youtube-monetization-policy-changes-2026-a-complete-dated-timeline) (2차), [Tubefilter 2026-01-29](https://tubefilter.com/2026/01/29/youtube-ai-slop-channel-crackdown-bans/)
- 수익화 불가 예시: "이미지 슬라이드쇼, 스크롤 텍스트, **추가 논평이 거의 없는 기사 자동 낭독**", "슬라이드쇼와 템플릿 스토리라인", "대량 생산 인상을 주는 일반 템플릿 AI 콘텐츠", "**표면적 차이만 있는 내레이션 스토리를 올리는 채널**", "**모두 같은 내레이션을 쓰는 슬라이드쇼 채널**" — [YouTube 고객센터: 채널 수익 창출 정책](https://support.google.com/youtube/answer/1311392?hl=en) (문구는 [AlternativeTo](https://alternativeto.net/news/2025/7/youtube-updates-its-policy-to-demonetize-inauthentic-mass-produced-ai-generated-content), [aivideocut](https://www.aivideocut.com/blog/youtube-tightens-monetization-rules-for-ai-generated-content) 검색 요약으로 재확인)
- YouTube는 원본 콘텐츠를 강화하는 AI 사용은 계속 수익화를 허용한다고 밝혔다 — [AlternativeTo](https://alternativeto.net/news/2025/7/youtube-updates-its-policy-to-demonetize-inauthentic-mass-produced-ai-generated-content)
- 건강·법률·금융·정치 등 민감 주제에서 사람 전문가처럼 행세하는 AI 페르소나는 수익화 불가다(이전 노트에서 인용, 유지) — [YouTube 고객센터](https://support.google.com/youtube/answer/1311392?hl=en)

**AI 라벨**
- Meta "AI info" 라벨은 페널티가 아니라 투명성 고지다. 사실적인 AI 생성 인물, 실존 인물의 가짜 언행, 카메라로 찍은 것처럼 보이는 사실적 장면이 주 대상이다. 2026년 광고 정책 정리 기준 AI로 만든 이미지·슬라이드쇼·영상은 모두 허용된다 — [Cinerads 2026 정리](https://www.cinerads.com/blog/ai-ugc-facebook-ad-policy) (광고 맥락 2차 정리), [APH Networks: 'Made with AI'→'AI info'](https://aphnetworks.com/index.php/news/28906-instagrams-made-ai-label-swapped-out-ai-info-after-photographers-complaints)
- TikTok: **사실적인(realistic) 이미지·오디오·영상**을 담은 AI 생성 콘텐츠에 라벨을 의무화했고 Content Credentials(C2PA)를 도입했다. 일러스트·만화의 면제 여부는 검색 결과로 명시 확인하지 못했다 — [NBC New York](https://www.nbcnewyork.com/news/national-international/tiktok-to-start-labeling-ai-generated-content-as-technology-becomes-more-universal/5399109/?amp=1), [TikTok 뉴스룸 2025-11](https://newsroom.tiktok.com/more-ways-to-spot-shape-and-understand-ai-content?lang=en)
- YouTube 합성 콘텐츠 공개는 "실제로 착각할 수 있는" 콘텐츠만 대상이고, 명백히 비현실적인 애니메이션 등은 제외된다(이전 노트 인용, 유지) — [YouTube 고객센터](https://support.google.com/youtube/answer/14328491)

**저작권**
- 사실과 아이디어는 저작권 보호 대상이 아니고 표현만 보호된다(아이디어-표현 이분법). 반면 학술지 논문의 **설명 문장·도표(figure)·삽화**는 일반적으로 보호되므로 재사용에는 허락이나 공정이용 판단이 필요하다. CC 라이선스 오픈액세스 논문은 조건(대개 저작자 표시)을 지키면 재사용할 수 있다 — [Muskulus, Copyright for Scientists](https://muskulus.folk.ntnu.no/blog/copyright-for-scientists/), [Project Alexandria (arXiv 2502.19413)](https://arxiv.org/pdf/2502.19413), [Lib4RI CC 라이선스 안내](https://www.lib4ri.ch/new-lib4ri-info-copyright-cc-licences)

**정확성**
- LLM 과학 요약의 과일반화 편향(§2 인용) — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12042776/)

### Inferences
- **4편/일 템플릿이 위험한가?** 대상 계정은 같은 레이아웃·같은 목소리·같은 길이를 반복한다. 겉모양만 보면 "같은 내레이션 구조의 슬라이드쇼 채널" 예시와 겹친다. 그러나 정책의 판정 축은 "표면적 차이만 있는가"다. 편마다 다른 논문·다른 서사·고유 드립·출처가 있으면 '추가 논평이 있는 해설'로 방어할 근거가 있다. 리스크가 커지는 조건은 ① LLM 요약을 그대로 낭독하고(고유 논평 없음) ② 대본 골격이 매 편 동일하며 ③ 하루 편수를 늘려 품질이 떨어질 때다. **편수보다 '편마다 고유한 해석이 있는가'가 관건이다**(추정, 정책 집행은 사례별).
- 이 계정은 Instagram 전용이다. Instagram에는 YouTube 같은 명시적 '불성실 콘텐츠 수익화 해제' 체계가 없다(보너스는 초대제, 아래 §6). 따라서 YouTube보다 Instagram에서 정책 리스크가 낮다(추정).
- **AI 라벨**: 판화풍 일러스트는 "사실적" 기준에 해당하지 않을 가능성이 높다. 남는 회색지대는 **사람처럼 들리는 TTS 나레이션**("realistic audio")이다. 실존 인물을 흉내 내는 것이 아니므로 기만 위험은 낮지만, 자발적 AI 고지가 가장 안전하다.
- **논문 figure 금지**: 레포 V4.0은 보도사진·SNS 캡처를 `credit`만 달고 쓰는 구조다. 이를 논문 포맷에 그대로 옮겨 **논문 도표 캡처를 붙이면 출처 표기만으로는 이용 허락이 되지 않는다**. 이는 V4.0 체크리스트(`shorts_format.py` NEWS_V4 checklist: "통신사 사진은 표기해도 이용 허락이 아니다")와 같은 논리다. 일러스트는 AI로 새로 그리고, 논문은 인용 표기(저널·제목·연도)만 하는 방식이 대상 계정의 방식이며 가장 안전하다.
- **정확성 리스크는 과학 소재 중 의학·건강에서 가장 크다**(예: 대상 계정의 지방간·미토콘드리아 편). YouTube에서 건강 주제는 '민감 주제' 범주와 의료 오정보 정책에 걸리므로 사실 검증 게이트가 필수다.

### Gaps
- YouTube 정책 페이지 원문 문구를 fetch하지 못해, 위 예시 문구는 2차 출처 검색 요약으로 재확인한 것이다.
- Meta의 2025~2026 **유기 게시물**(광고 아님) AI 라벨 정책에서 "realistic-sounding audio"가 TTS 내레이션을 포함하는지 원문 확인 실패.
- 한국 저작권법 제28조(공표된 저작물의 인용)를 논문 figure에 적용한 해석 자료는 찾지 못했다.

## 4. ContentsMaker 파이프라인 적합성 (V4.0 news_v4 대비)

### Takeaway
**V4.0(news_v4)이 가장 가까운 골격이다.** 사진 슬롯 타이머, 호흡 단위 자막 분할, 1회 호출 Charon TTS + 무음 정렬, BGM 없음, 2줄 헤드라인, 출처 줄, `fact_sources` 게이트를 그대로 재사용할 수 있다. 바꿔야 할 것은 다섯 가지다. ① **길이 캡**: 현재 news_v4는 62초, V5만 70초인데 이 포맷은 99~170초다. ② **카테고리 하드 차단**: political/entertainment/society 외는 ValueError다. ③ 일러스트 생성 스타일 프리셋. ④ 크림 캔버스·자막 스타일. ⑤ 정치 전용 게이트(CTA 선택지형, 진영 대칭, 보도체 제목, Charon 뉴스캐스터 톤) 면제. 새 포맷 키(예: `knowledge_v6`)를 `FormatRules`에 추가하는 방식이 가장 작은 변경이다.

### Cited Findings (레포 직접 확인)
**재사용 가능**
- 사진 트랙: `scripts/news_v4_timeline.py` l.52~70 `photo_schedule()`는 첫 사진을 첫 문장 끝까지, 이후 `DEFAULT_INTERVAL_MS = 3400`(l.18) 고정 간격으로 배치하고 모자라면 `photos[1:]`을 순환한다. 사진별 `dur`(초) 지정은 `_dur_ms()` l.43~45가 지원한다. → 일러스트 1장당 13~22초를 `dur`로 지정하면 대상 포맷을 재현할 수 있다.
- 자막: `news_v4_timeline.py` l.20 `DEFAULT_CAPTION_CHARS = 16`, `split_caption()` l.109, `caption_chunks_for_scene()` l.134. 나레이션을 어절 경계로 쪼개 글자 수 비례로 시간을 배분한다. 대상 계정의 "2~3줄, 3~5초마다 교체"와 단위만 다르다(16자 1줄 → 2~3줄 묶음).
- TTS: `scripts/render_news_v4.py` l.331~346 `_tts_raw()`(Gemini Charon, `find_reusable_tts` 재사용 `--reuse-tts`), l.349~359 `_synthesize()`(`align_timings_to_silence` + 배속).
- BGM 없음: `render_news_v4.py` l.73~75 `USE_BGM = False`(코드 고정). 대상 계정도 `music_info:null`이다(BGM 유무는 미확정, `account_catalog.md` §2 Gaps).
- 출처 게이트: `render_news_v4.py` l.126 `_gate_fact_sources(cfg)`(원본은 `scripts/render_profile_v3.py` l.144, 나무위키 차단 `BANNED_FACT_HOSTS` l.73). 하단 출처 줄 `photo_credit_label()` l.197, `CREDIT_PREFIX = "출처 : "` l.70. 대상 계정의 캡션 `출처 : 저널, 제목, 연도`와 문법이 같다.
- 밝은 캔버스 렌더 경로: `render_news_v4.py` l.379~389 `render_video(... respect_background_colors=True, headline_color=HEADLINE_COLOR, overlay_boxes=False, headline_plain=True, news_card=card)`. 캔버스 기본값은 `render_profile_v3.py` l.84 `DEFAULT_BG_COLORS = ("#F5F5F5", "#F5F5F5")`, 헤드라인 l.87 `#111111` → 크림(`#F3EBDD` 계열)으로 바꾸는 것은 config `bg_colors`로 가능하다(`render_news_v4.py` l.245).
- Remotion 레이어: `src/video/remotion/src/components/NewsCardLayer.tsx` l.28~31 `NEWS_BOX_TOP = 440`, `BOX_SIZE = 1080`(정사각 박스), l.33 `CREDIT_BOTTOM = 190`, l.34~36 켄 번즈 줌 `ZOOM_COVER 0.12 / ZOOM_CONTAIN 0.04`. 대상 계정의 "중앙 일러스트 1장 + 느린 정지"에 맞고, 판화 일러스트는 `fit: "contain"`(약한 줌)이 적합하다.
- 이미지 가드: `src/illustrator/image_constants.py` `NO_TEXT_GUARD`(글자 없는 일러스트 강제)를 그대로 쓴다. 판화풍에는 사진용 `PHOTO_STYLE_PREFIX/FOOTER`(anti-illustration 문구 포함)를 **쓰면 안 된다**.
- 업로드 자동화: `src/upload/youtube_uploader.py`, `tiktok_uploader.py`는 있다(CLAUDE.md). Instagram 업로더는 레포에 없다(아래 결핍).

**바꿔야 할 것 (충돌·결핍)**
1. **길이 캡**: `scripts/political_length.py` l.19 `TARGET_MAX_SEC = 62.0`(하드 캡, 2026-08-31에 42→62초), l.85~96 `max_final_sec()`가 `FormatRules.max_final_sec`를 우선 적용한다. `shorts_format.py` NEWS_V4(l.127~)는 이 값이 없어 62초, EVIDENCE_V5만 l.166 `max_final_sec=70.0`이다. `render_news_v4.py` l.369~370 `enforce_length()`가 렌더 전에 차단한다. → 새 포맷 규칙에 `max_final_sec=180.0`(Instagram/Shorts 3분 상한)을 넣으면 코드 변경 없이 풀린다. **주의**: 과제 설명의 "프로젝트 캡 ~42–70초"는 현재 코드 기준으로 **62초(기본)/70초(V5)**다.
2. **카테고리 하드 차단 3중**:
   - `render_news_v4.py` l.63~66 `ALLOWED_CATEGORIES = (POLITICAL, "entertainment", "society")`, l.116~119에서 그 밖이면 ValueError.
   - `scripts/shorts_category.py` l.30 `CATEGORIES = ("political", "economic", "society", "entertainment")`, l.139~141 미지 카테고리 ValueError. 키워드 추론 l.48~ 에 과학 키워드가 없다.
   - `scripts/shorts_domain.py` l.92~ `_build_domain_rules()`가 4종만 만들고, l.241~244 `rules_for()` ValueError. `emotion_type`/`bg_colors` 기본값도 카테고리별(l.109~216)이다.
   → `science`(또는 `knowledge`) 카테고리를 세 곳에 추가하거나, 새 렌더러에서 카테고리 축을 우회해야 한다. 036 원장(`data/channel_analytics/category_ledger.json`)에 5번째 축이 생긴다.
3. **정치 전용 게이트 상속**: `render_news_v4.py` l.86~88 `load_config()`가 `political_cta.apply_cta`를 적용하고, l.149~151 `config_warnings()`가 V2.1 경고(035 CTA 질문형, 039 돌파, 040 대칭)를 그대로 재사용한다. NEWS_V4는 `symmetry_applies=True`, `default_cta_style=CTA_STYLE_PICK`이다(`shorts_format.py` l.127~136). 대상 포맷에는 선택지형 CTA가 없고 진영도 없다 → 새 FormatRules에서 `symmetry_applies=False`, CTA 면제(새 스타일 또는 `subscribe`) 처리가 필요하다.
4. **보도체 제목 게이트**: `render_news_v4.py` l.128~131 → `political_upload_package.gate_yt_title`(l.73~)이 해시태그·과거형 어미를 차단한다. 대상 계정 제목("핵실험 흔적이 고래 이빨", "멧돼지")은 명사형이라 대체로 통과할 것으로 보인다(추정). 업로드 패키지·3줄요약(038)은 그대로 쓸 수 있다.
5. **TTS 톤**: `render_profile_v3.py` l.79~80 `V2_1_TTS_STYLE_PROMPT = "Read in a fast, clear newscaster tone with neutral political delivery:"`. 대상 포맷은 존댓말 + 드립의 이야기꾼 톤이다. 041 실측에서 Gemini TTS 체감 속도와 톤은 이 style_prompt 문구로 결정됐다(CLAUDE.md 041). → 새 style_prompt와 음성(Charon 외 후보) 선택이 필요하다.
6. **source_type**: `render_news_v4.py` l.236 `source_type="political_pro"`가 박혀 있다. BGM이 꺼져 있어 지금은 무해하지만, 업로드 메타·통계에서 정치로 섞인다 → 새 값(`knowledge`) 권장.
7. **자막 스타일**: `NewsCardLayer.tsx` l.127 `fontSize = lines.length > 1 ? 72 : 60`, l.146 `background: "rgba(0,0,0,0.88)"`(검은 박스 + 흰 글자). 대상은 크림 배경 위 검은 글자, 박스 없음, 2~3줄이다 → 옵트인 프롭(예: `captionPlain`, 줄 수)을 추가해야 한다. 042/043이 해 온 "미지정 시 기존 still 바이트 동일" 방식을 따른다.
8. **일러스트 생성**: `src/illustrator/prompt_builder.py` l.86~133 `IMAGE_STYLE_PRESETS`는 webtoon/3d_pixar/realistic/anime 4종뿐이다 → `vintage_engraving` 프리셋을 추가해야 한다(크로스해칭·세피아·cream background·single isolated subject + `NO_TEXT_GUARD`). 레퍼런스 이미지는 l.293/313 `use_refs = refs_available() and image_style == "webtoon"`, `src/illustrator/image_generator.py` l.95~96이 webtoon 외에는 끈다. 화풍 고정은 키워드 반복에 의존해야 한다. 비율: `freepik_image_gen.py` l.83 `aspect_ratio="9:16"` 기본(`"1:1"` 지원)이지만, `gemini_web_image_gen.py` l.181은 프롬프트에 "(9:16 세로)"를 하드코딩한다 → NewsCardLayer의 1080 정사각 박스에 맞추려면 1:1 생성 경로가 필요하다.
9. **V4.0 사진 수집 전제**: `render_news_v4.py` l.60~66 `MIN_PHOTOS = 4`, `_validate_photos`(l.136), `photos[*].credit` 필수, `photos-sheet`(l.301)는 "인물 본인 확인"용이다. 일러스트 포맷에서 credit은 "AI 생성" 같은 고정값이 된다.
10. **Instagram 업로드 없음**: `src/upload/`에는 YouTube·TikTok만 있다. Instagram Graph API 게시(24h 50건)를 붙이거나 MBS로 수동 예약해야 한다.

### Inferences
- **최소 구현 경로(추정)**: `scripts/render_knowledge_v6.py`(render_news_v4 복제 후 위 2·3·5·6 수정) + `_template_knowledge_v6.json` + `shorts_format.py`에 `FormatRules(format="knowledge_v6", max_final_sec=180.0, symmetry_applies=False, intro_required=False, default_cta_style=…)` + `NewsCardLayer` 옵트인 자막 프롭 + `prompt_builder` `vintage_engraving` 프리셋. 기존 V4.0 동작은 그대로 둔다. 새 기능이고 3개 이상 파일을 고치므로 CLAUDE.md HARD-GATE상 `/plan`이 먼저다.
- 사진 타이머를 고정 3.4초 대신 **씬(세그먼트) 경계에 맞추는 모드**가 대상 포맷에 더 맞는다. 대상 계정은 일러스트를 주제 전환 시점(4.3/16.8/32.7초…)에 바꾸고, 이는 문장 그룹 경계로 보인다. `photo_schedule()`에 scene 매핑 옵션을 추가하거나 `dur`를 TTS 타이밍에서 역산하면 된다.
- **무음 정렬 리스크**: 대상 포맷처럼 문장 사이 무음이 거의 없는 2분 연속 나레이션은 `align_timings_to_silence`의 앵커가 줄어든다. 자막 동기 오차가 커질 수 있으므로 실렌더로 검증해야 한다(추정).
- 1회 호출 TTS의 런어웨이(무음 삽입으로 수백 초가 되는 현상, 메모리 `charon-tts-runaway-cache`)는 대본이 2배 길어지면 발생 확률이 오를 수 있다(추정). 세그먼트 단위 분할 호출 옵션을 고려할 만하다.
- 대본 생성은 레포의 `src/analyzer/`(Claude/Gemini)를 재사용할 수 있다. 그러나 §2의 과일반화 연구 때문에 "초록·결론 원문 문장 ↔ 대본 주장" 대조 체크리스트를 `fact_sources` 게이트와 함께 두어야 한다.

### Gaps
- 2분 Gemini TTS 1회 합성의 안정성(런어웨이, 5,000자 이내 실측 길이)은 실험하지 않았다.
- `NewsCardLayer`의 1080 정사각 박스에 판화 컷아웃이 들어갔을 때 대상 계정과 같은 여백감이 나오는지 still 렌더로 확인하지 않았다.

## 5. 채널 전략 적합성: 같은 채널 / 별도 채널 / Instagram 우선

### Takeaway
**별도 계정, Instagram 우선**을 권한다. 현재 YouTube 채널은 정치·사회·연예·경제 시사 쇼츠로 측정·게이트 체계가 짜여 있다(036~044). 2분 과학 썰은 길이·톤·시청 동기가 모두 다르다. 이 포맷의 벤치마크 근거(@hamster.743606)도 Instagram에서 나왔다. YouTube는 2차 배포처로, 불성실 콘텐츠 정책을 감안해 별도 채널에서 검증하는 편이 안전하다.

### Cited Findings
- 현재 채널 편성 목표: political 40 / society 25 / entertainment 20 / economic 15%. 소재 선정은 039 돌파 3문항(민간인·대가·당내 절차 아님)이고, 044 진단은 "정치 편중으로 2주 중앙값 2,356 → 1,318 하락"이다 — `CLAUDE.md` Key Conventions 039/040/044, Recent Changes 044
- 채널 실측 길이 최적치: 035에서 38~42초 캡, 이후 62초로 상향. V5만 70초. 근거는 "상위권 2편이 38·40초" — `scripts/political_length.py` l.1~19
- 카테고리 혼합 시 희석 경고 장치: `analyze_channel_performance.py` `category_mix_warnings()`(036) — `CLAUDE.md` 036
- YouTube 수익화 정책은 **채널 단위**로 심사된다(불성실 콘텐츠 판정이 채널 전체 수익화에 영향) — [YouTube 고객센터](https://support.google.com/youtube/answer/1311392?hl=en)
- Instagram 한국 수익화: 기프트·구독·보너스 프로그램이 도입됐지만 보너스는 100% 초대제다 — [디지털인사이트](https://ditoday.com/%ec%9d%b8%ec%8a%a4%ed%83%80%ea%b7%b8%eb%9e%a8-%ec%83%88%eb%a1%9c%ec%9a%b4-%ec%88%98%ec%9d%b5-%ec%b0%bd%ec%b6%9c-%eb%8f%84%ea%b5%ac%eb%a1%9c-%ed%81%ac%eb%a6%ac%ec%97%90%ec%9d%b4%ed%84%b0-%ec%a7%80/), [Filmora](https://filmora.wondershare.kr/basic-concept/what-is-instagram-reels-monetization.html)

### Inferences
- **같은 채널에 넣으면 안 되는 이유(추정)**: ① 시청자 기대 불일치(시사 판정형 CTA "누가 잘못?" vs 교양 썰) ② 036 카테고리 원장·040 편성 비중·044 추천기에 5번째 축이 생겨 측정이 오염된다 ③ 2분 영상이 채널 평균 시청 시간·완주율 지표를 흔든다 ④ 4편/일 템플릿 물량이 불성실 콘텐츠 심사에 걸리면 **기존 시사 채널의 수익화까지 함께** 위험해진다.
- **Instagram 우선 근거(추정)**: 벤치마크가 Instagram에서 약 3~4주 만에 1.6만 팔로워(개설일은 미확인)를 모았다. Instagram은 3분 릴스와 저장·공유 중심 신호가 이 포맷에 유리하다. YouTube식 수익화 해제 리스크도 없다. 대신 Instagram 직접 수익은 초대제 보너스 외에는 약하므로, 수익 모델(광고 협찬, 링크인바이오, 후속 YouTube 롱폼 전환)을 따로 정해야 한다.
- **YouTube 별도 채널은 2단계**: 같은 mp4를 Shorts(3분 이하)로 올릴 수 있지만, 2분 Shorts가 피드에서 어떻게 소비되는지는 미검증이다. 별도 채널에서 8~10편 파일럿 후 판정하는 기존 방식(041 V3.0 판정법)을 따르는 것이 일관적이다.
- **코드베이스는 공유**: 렌더러·TTS·Remotion·업로드 패키지를 공유하고, `format`·`category`·`source_type` 축으로 격리하는 것이 레포 관행(041~043)과 맞는다.
- **소재 측면 연결**: 044 추천기(네이버 댓글 많은 뉴스)는 시사 전용이라 이 포맷의 소재원이 아니다. 과학 썰 소재원은 신규 논문 피드(저널 RSS, EurekAlert 등)가 되어야 한다(추정). 정치·건강 논문은 §3 리스크(민감 주제·의료 오정보) 때문에 초기 소재에서 제외하는 편이 안전하다.

### Gaps
- 사용자가 Instagram 계정을 운영할 의사가 있는지, 운영 리소스(하루 4편 대본 검수)를 감당할 수 있는지는 사용자 결정 사항이다.
- 별도 채널의 기대 성과를 뒷받침할 이 사용자 채널의 실측은 없다(과학 소재 0편).
- 대상 계정의 조회수가 없어(로그아웃 수집 한계) "논문형 > 드립형" 결론은 좋아요 8편 비교에 근거한 약한 신호다.
