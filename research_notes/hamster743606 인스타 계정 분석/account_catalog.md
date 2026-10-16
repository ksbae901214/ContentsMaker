# @hamster.743606 인스타그램 계정 카탈로그 (관측일 2026-10-14 15:22 KST)

> **수집 방법 (중요)**: Claude-in-Chrome 확장이 연결되어 있지 않았다(`list_connected_browsers` = 빈 목록). 그래서 로그인 없이 curl 로 수집했다.
> - 프로필/그리드: `https://www.instagram.com/hamster.743606/` 를 Googlebot UA 로 요청 → 페이지 내장 JSON(`xig_user_by_igid_v2`, `polaris_timeline_connection`)에서 추출.
> - 게시물별: `https://www.instagram.com/p/<shortcode>/` 를 Googlebot UA 로 요청 → `like_count`, `comment_count`, `taken_at`, 캡션, 오디오 정보, DASH 매니페스트(영상 길이)를 추출.
> - **한계**: 로그아웃 상태 그리드는 **최근 12개만** 노출된다. 다음 페이지 GraphQL 요청은 `xig_user_by_igid_v2: null` 을 반환했고, 미러 사이트(imginn/picuki/pixwox/dumpor/greatfon)는 전부 Cloudflare 차단. 그래서 **91개 중 12개만** 수집했다. **조회수(play/view count)는 로그아웃 응답에 없다** → 조회수는 하나도 확보하지 못했다.
> - 영상 3편(DeZMeEIgyot, Dec1xpsAXZX, DeXsKpVAnP9)은 DASH 스트림을 받아 ffmpeg 프레임 샘플링 + faster-whisper(small) 전사로 포맷을 확인했다. 전사에는 오인식이 있다(예: "수확" = 수학).

## 1. 프로필 기본 정보

### Takeaway
"햄스터"라는 닉네임을 쓰는 한국어 1인 크리에이터(본업 전략기획 + 앱 개발자라고 자기소개) 계정이다. 동물·생물·물리·역사 같은 "신기한 이야기"를 **약 2분짜리 일러스트 슬라이드 + 한국어 나레이션 릴스**로 하루 3~5편 올린다. 팔로워 16,424명, 게시물 91개, 팔로잉 4명.

### Cited Findings
- 표시 이름 `햄스터`, 핸들 `hamster.743606`, 인증 배지 없음(`is_verified:false`), 공개 계정(`is_private:false`), 릴스 있음(`has_any_clips:true`). 내부 user pk `70459925096`. — [Instagram 프로필](https://www.instagram.com/hamster.743606/)
- 팔로워 **16,424** / 팔로잉 **4** / 게시물 **91** (og:description 표기는 "16K Followers, 4 Following, 91 Posts"). — [Instagram 프로필](https://www.instagram.com/hamster.743606/)
- 바이오 원문(4줄): "낮엔 전략 기획, 밤엔 앱 개발. / 신기한 동물·생물·물리 이야기 좋아합니다. / 팔로우 하시고 재밌고 유익한 글 많이 가져가세요. / 전체 글 다시보기 :" — 마지막 줄 뒤에 링크가 있는 것으로 보이지만, 로그아웃 응답에는 링크 URL(`bio_links`/`external_url`)이 없었다. — [Instagram 프로필](https://www.instagram.com/hamster.743606/)
- 하이라이트: 로그아웃 쿼리 변수에 `should_enable_highlights_tray:false` 가 들어 있어 이 경로로는 확인할 수 없었다. `latest_reel_media:0` 이라 관측 시점에 활성 스토리는 없다. — [Instagram 프로필](https://www.instagram.com/hamster.743606/)
- 모든 영상 우하단에 `made by 햄스터` 워터마크가 있다(프레임 확인). — [Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)

### Inferences
- 언어/국가: 캡션·나레이션·자막이 모두 한국어이고, 업로드 시각이 KST 기준 07~21시 정각대에 몰려 있다 → 한국 기반 계정으로 추정.
- 바이오의 "전체 글 다시보기"는 블로그나 웹앱 같은 아카이브로 연결되는 링크로 추정된다. 본인 소개가 "앱 개발"이라 자체 제작 사이트일 가능성이 있다(미확인).
- 팔로잉 4명, 개인 일상 콘텐츠 0 → 콘텐츠 전용 채널.

### Gaps
- 계정 카테고리, 크리에이터/비즈니스 여부(`is_business_account`, `category_name`)는 로그아웃 응답에 없어 확인하지 못했다.
- 링크인바이오 URL, 하이라이트 목록, 연결된 TikTok/YouTube/Threads는 확인하지 못했다. WebSearch 로도 핸들이나 바이오 문구가 검색되지 않았다.
- 계정 개설일("이 계정 정보")은 로그인해야 보여서 확인하지 못했다.

## 2. 계정 니치/콘셉트 (실제로 본 것)

### Takeaway
실제 햄스터 계정이 아니다. **"지식 썰 나레이션 + 레트로 판화풍 일러스트 슬라이드"** 포맷이다. 주제는 크게 두 갈래다: (A) 최신 학술논문 1편을 썰로 푼 과학 이야기(캡션에 `출처 : 저널명, 논문 제목, 연도`), (B) 사물·동물·취미·역사를 의인화하거나 "허당 설계"로 비꼬는 드립형 해설(멧돼지, 제주도 낚시, 헬스장, 타짜 도박판, 롤스로이스, 에니그마).

### Cited Findings
- 화면 구성(12편 썸네일 + 1편 프레임 16장 확인): 크림/베이지 단색 배경, 상단 중앙 **검은 굵은 고딕 제목**(캡션 첫 줄과 같은 문장으로 보임), 중앙 **빈티지 판화·레트로 일러스트 1장**(소재 하나를 흰 배경에 컷아웃), 하단 중앙 **2~3줄 검정 자막**, 우하단 `made by 햄스터`. 9:16, 720×1280, 30fps. — [Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)
- 일러스트 전환: 120.5초 영상에서 장면 전환이 4.3/16.8/32.7/49.8/66.4/82.9/104.6초에 있다 → **일러스트 8장, 장당 약 13~22초**. 자막은 문장 단위로 약 3~5초마다 바뀐다(ffmpeg scene 0.01 임계값). — [Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)
- 오디오: 모든 12편이 `Original audio` (ig_artist = hamster.743606), `music_info:null` → 라이선스 음원 미사용, 자체 나레이션 오디오. 평균 음량 -16.4dB, 최대 -4.1dB, -40dB 이하 0.3초 이상 무음 구간 7회뿐 → 문장 사이가 거의 비지 않는 연속 나레이션. — [Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)
- 나레이션 대본 예시(베이즈 정리 편, 전사): "1968년 미국 핵잠수함 한 척이 대서양 한가운데서 감쪽같이 사라집니다"로 시작해 → 과학자 등판 → "위스키 걸고 베팅합시다" 일화 → 사전확률 설명 → 실패도 정보 → "예측 지점에서 오차는 고작 220m" → 교훈("새 정보가 들어올 때마다 유연하게 생각을 고쳐먹는 것") → "18세기 목사님이 끄적거린 확률 공식이었다는 게 레전드입니다"로 마무리. 문장은 전부 "~합니다/입니다" 존댓말 + 구어 드립("골 때렸습니다", "삽질", "똥고집"). — [Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)
- 드립형 예시(멧돼지 편): 첫 문장 "산에서 마주치면 세상에서 제일 무서운 동물인데 가만히 뜯어보면 어딘가 나사 빠진 구석이 한둘이 아닙니다" → 소주제를 "하늘을 못 본다 / 시력 0.1 / 브레이크 없음 / 송진 갑옷 / 새끼는 수박" 식으로 나열 → 게임 비유("스탯", "코는 최첨단 레이더인데 모니터 해상도는 144p", "풀악셀") → "정리하면…" 요약 → "압도적인 힘과 맷집 하나로 모든 허당 설계를 뚫고 살아가는 생물" 마무리. — [Reel Dec1xpsAXZX](https://www.instagram.com/reel/Dec1xpsAXZX/)
- 제주도 낚시 편: 낚시꾼 고생담을 과장 비유로 쭉 나열("1톤 트럭이 낚싯줄 걸고 풀악셀", "신내림 굿판") → 공항 면세점 펀치라인으로 끝. — [Reel DeXsKpVAnP9](https://www.instagram.com/reel/DeXsKpVAnP9/)
- 캡션은 극단적으로 짧다: 제목 한 줄만 쓰거나(예: "멧돼지", "롤스로이스"), 논문 편은 제목 + `출처 : 저널, 논문 제목, 연도`. **해시태그 0개**(12편 전부). — [Instagram 프로필](https://www.instagram.com/hamster.743606/)

### Inferences
- 일러스트는 같은 화풍(빈티지 판화, 제한된 팔레트)이 일관되게 반복된다 → AI 이미지 생성으로 추정(미확인).
- 나레이션 음성이 사람인지 TTS인지는 확인하지 못했다. 문장 간 무음이 거의 없고 문장 단위로 균일한 점은 TTS 같은 합성 음성에 가깝다(추정).
- "제목 고정 + 일러스트 + 문장 자막" 구조는 정적 이미지에 오디오만 바뀌는 형태라, ContentsMaker의 V4.0(news_v4: 사진 슬라이드 + 전체 TTS + BGM 없음)과 구조가 매우 가깝다. 차이는 ①길이 100~170초(우리 캡 42~70초), ②일러스트 1장 고정 노출이 13~22초로 김, ③정치·뉴스가 아닌 교양·드립.

### Gaps
- BGM 유무는 음량 분석만으로 단정하지 못했다(연속 음원이 깔렸을 가능성 있음).
- 12편 이전(79편)의 주제 분포는 확인하지 못했다.

## 3. 게시물별 표 (최근 12편, 전부 Reels, 고정 게시물 없음)

### Takeaway
12편 모두 릴스(`product_type: clips`)이고 길이는 99~170초(중앙값 126.4초)다. 좋아요 중앙값은 292(전체 12편), 게시 후 24시간 이상 지난 8편만 보면 384다.

### Cited Findings
업로드 시각은 `taken_at`(UTC epoch)을 python 으로 KST 변환. 좋아요/댓글은 2026-10-14 15:22 KST 관측값. "경과"는 관측 시점까지 시간. 조회수는 확보하지 못했다(로그아웃 응답에 없음). 해시태그는 전부 0개, 오디오는 전부 Original audio(hamster.743606).

| # | 업로드(KST) | 경과 | 코드(링크) | 길이(초) | 좋아요 | 댓글 | 댓글/좋아요 | 캡션(전문 또는 첫 줄) | 유형 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-14 수 15:07 | 0.3h | [Dedsz9pAuOF](https://www.instagram.com/reel/Dedsz9pAuOF/) | 115.2 | 0 | 0 | - | AI 증류 전쟁 | 시사/기술 |
| 2 | 2026-10-14 수 11:06 | 4.3h | [DedRTpqAYFY](https://www.instagram.com/reel/DedRTpqAYFY/) | 139.6 | 90 | 7 | 7.8% | 롤스로이스 | 사물·브랜드 |
| 3 | 2026-10-14 수 07:06 | 8.3h | [Dec1xpsAXZX](https://www.instagram.com/reel/Dec1xpsAXZX/) | 128.9 | 589 | 50 | 8.5% | 멧돼지 | 동물 드립 |
| 4 | 2026-10-13 화 18:06 | 21.3h | [DebcmKDg06A](https://www.instagram.com/reel/DebcmKDg06A/) | 147.4 | 140 | 11 | 7.9% | 좀비가 철학적 사고실험이 된 | 철학 |
| 5 | 2026-10-13 화 15:06 | 24.3h | [DebH8AxgBcB](https://www.instagram.com/reel/DebH8AxgBcB/) | 123.9 | 470 | 8 | 1.7% | 핵실험 흔적이 고래 이빨 / 출처 : Frontiers in Marine Science, Integrating radiocarbon and stable isotopes in odontocete teeth to reveal life histories, 2026 | 논문 |
| 6 | 2026-10-13 화 11:06 | 28.3h | [DeasgWygytS](https://www.instagram.com/reel/DeasgWygytS/) | 170.2 | 235 | 14 | 6.0% | 에니그마 | 역사·기술 |
| 7 | 2026-10-12 월 21:07 | 42.3h | [DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/) | 120.5 | **961** | 30 | 3.1% | 베이즈 정리로 실종된 잠수함 / 출처 : Naval Research Logistics, Operations analysis during the underwater search for Scorpions, 1971 | 논문(역사) |
| 8 | 2026-10-12 월 18:07 | 45.3h | [DeY3zw6gxQ1](https://www.instagram.com/reel/DeY3zw6gxQ1/) | 155.3 | 83 | 9 | 10.8% | 타짜 도박판 | 취미·문화 드립 |
| 9 | 2026-10-12 월 15:07 | 48.3h | [DeYjONDgW7J](https://www.instagram.com/reel/DeYjONDgW7J/) | 99.0 | 816 | 34 | 4.2% | 오랑우탄 엄마는 새끼의 / 출처 : Proceedings of the National Academy of Sciences, Maternal ranging strategies facilitate offspring social play at energetic cost in the most solitary ape, 2026 | 논문(동물) |
| 10 | 2026-10-12 월 11:05 | 52.3h | [DeYHm5cgFRN](https://www.instagram.com/reel/DeYHm5cgFRN/) | 119.6 | 286 | 18 | 6.3% | 헬스장 운동 | 취미 드립 |
| 11 | 2026-10-12 월 07:06 | 56.3h | [DeXsKpVAnP9](https://www.instagram.com/reel/DeXsKpVAnP9/) | 134.5 | 674 | 64 | 9.5% | 제주도 낚시 | 취미 드립 |
| 12 | 2026-10-11 일 21:05 | 66.3h | [DeWndUrgMZY](https://www.instagram.com/reel/DeWndUrgMZY/) | 109.7 | 298 | 21 | 7.0% | 지방간 악화를 막는 '미토콘드리아 / 출처 : Nature Metabolism, UBE2N deficiency contributes to MASH development via p62-regulated mitophagy and PANoptosis, 2026 | 논문(의학) |

- 모든 원본 크기 720×1280(9:16), `like_and_view_counts_disabled:false`, `is_timeline_pinned:false`, 공동작성자·위치 태그 없음. — 위 각 게시물 링크
- 캡션 제목이 문장 중간에서 잘린 형태가 반복된다("오랑우탄 엄마는 새끼의", "좀비가 철학적 사고실험이 된", "지방간 악화를 막는 '미토콘드리아"). 영상 상단 제목도 똑같이 잘려 있다(썸네일 확인). — [Instagram 프로필](https://www.instagram.com/hamster.743606/)

### Inferences
- 제목이 문장 중간에서 끊기는 건 글자 수 제한 템플릿이 자동으로 자른 결과로 보인다. 그래서 의도치 않게 호기심 유발형 미완결 제목이 된 것으로 추정한다.

### Gaps
- 조회수 0건 확보 → 조회수 기준 상위 10, 조회수 중앙값은 산출 불가.
- 나머지 79편(약 9/21~10/11 추정 구간)은 수집 불가. 로그인 브라우저로 Reels 탭(`/hamster.743606/reels/`)을 열어야 조회수와 전체 목록을 얻을 수 있다.

## 4. 업로드 주기 · 시작 시점 · 성장 신호

### Takeaway
관측된 12편은 2.75일 동안 올라왔다(하루 약 4.0편, 주 약 28편). 업로드는 매일 **07:06 / 11:06 / 15:07 / 18:07 / 21:07 KST** 슬롯에 분 단위까지 일정하게 들어가 예약 업로드로 보인다. 이 속도가 계속됐다면 91편째까지 역산한 시작점은 **2026-09-21(월) 전후**(추정)다.

### Cited Findings
- 연속 업로드 간격(시간, python 계산): 10.01, 4.0, 4.02, 3.0, 3.0, 13.99, 4.0, 3.01, 12.99, 4.01, 4.0. 10/12(월)은 07·11·15·18·21시 5편, 10/13(화)은 11·15·18시 3편, 10/14(수)는 07·11·15시 3편(관측 시점까지). — 위 게시물 `taken_at`
- 팔로워 16,424명 대비 좋아요율: 최고 5.85%(베이즈 961), 중앙 편은 약 1.8%. — 위 표 및 [프로필](https://www.instagram.com/hamster.743606/)

### Inferences
- 시작일 2026-09-21 은 "91편 ÷ 하루 4.0편"을 단순 역산한 값이다. 실제 개설일이나 첫 게시일과 다를 수 있다(**추정**).
- 이 추정이 맞다면 약 3~4주 만에 팔로워 1.6만명을 모은 셈이라 빠른 성장 신호로 읽히지만, 개설일을 확인하지 못해 검증되지 않았다.
- 게시 8시간 만에 좋아요 589(멧돼지)라는 수치는 최근 편도 꾸준히 도달하고 있다는 신호다.

### Gaps
- 팔로워 증감 추이(과거 시점 팔로워 수)는 확보하지 못했다.

## 5. 아웃라이어 vs 중앙값

### Takeaway
좋아요 기준 상위 편은 **학술논문 기반(출처 표기) 과학 썰**과 **'허당/고생' 드립형 동물·취미 편**이다. 같은 드립형이어도 "타짜 도박판", "에니그마", "좀비 사고실험"처럼 지식 진입장벽이 있거나 소재가 추상적인 편은 중앙값 아래에 머물렀다.

### Cited Findings (python 계산)
- 좋아요 중앙값: 전체 12편 **292** (평균 386.8) / 24시간 이상 경과 8편 **384** (평균 477.9).
- 댓글 중앙값: 전체 12편 **16** / 24시간 이상 8편 **19.5**.
- 길이: 중앙값 126.4초, 최소 99.0, 최대 170.2, 평균 130.3.
- 좋아요 순위: 베이즈 잠수함 961 > 오랑우탄 816 > 제주도 낚시 674 > 멧돼지 589(8h) > 고래 이빨 470 > 지방간 298 > 헬스장 286 > 에니그마 235 > 좀비 140 > 롤스로이스 90(4h) > 타짜 83 > AI 증류 0(0.3h).
- 논문 출처 표기 4편 좋아요 [470, 961, 816, 298] 중앙값 **643** vs 출처 없는 24시간 이상 4편 [235, 83, 286, 674] 중앙값 **260.5**.
- 댓글/좋아요 비율은 드립형이 높다(타짜 10.8%, 제주 9.5%, 멧돼지 8.5%). 논문형은 낮다(고래 1.7%, 베이즈 3.1%, 오랑우탄 4.2%). — 위 표

### Inferences
- 논문형은 저장·좋아요형(조용한 소비), 드립형은 댓글형(경험 공유)으로 반응이 갈리는 것으로 보인다. 표본이 4 대 4라 확정할 수 없다.
- 베이즈 편(최고)과 오랑우탄 편은 모두 "의외의 결말 + 숫자(220m 등)"가 있는 서사형이다.

### Gaps
- 경과 시간이 다른 편들을 같은 시점에 비교했다(0.3h~66h). 정규화된 비교가 아니다.
- 표본 12편이라 상위 10 아웃라이어 판정은 의미가 약하다.

## 6. 고정 게시물

### Takeaway
로그아웃 그리드 12편 중 고정(`is_timeline_pinned:true`) 게시물은 0개다.

### Cited Findings
- 12편 모두 `is_timeline_pinned:false`. — [Instagram 프로필](https://www.instagram.com/hamster.743606/)

### Gaps
- 로그아웃 그리드가 고정 게시물을 아예 빼고 보여줄 가능성은 배제하지 못했다. 로그인 브라우저로 재확인이 필요하다.
