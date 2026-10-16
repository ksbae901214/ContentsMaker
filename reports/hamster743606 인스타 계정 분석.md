# 판화 일러스트 2분 지식썰, V4.0 위에 올린다

@hamster.743606은 햄스터 캐릭터 계정이 아니다. 크림색 배경 위에 빈티지 판화풍 일러스트 8장을 깔고, 여성 음역 TTS가 존댓말과 게임 비유 드립을 섞어 2분 동안 "신기한 동물·과학·사물 이야기"를 들려주는 **한국어 지식 스토리텔링 릴스 채널**이다. 팔로워는 **16,424명, 게시물 91개**다. 매일 07·11·15·18·21시 정각대에 예약 업로드하는 것으로 보인다 ([Instagram 프로필](https://www.instagram.com/hamster.743606/)). 공개된 12편을 프레임·오디오 단위로 측정해 보니 레이아웃, 컷 리듬, 말 속도, 음량이 상위 편과 하위 편 사이에 **완전히 같았다**. 좋아요를 가른 것은 제작 품질이 아니라 **대본과 소재**다. 사건이나 숫자로 여는 짧은 논문 썰은 좋아요가 높았고, 일반론으로 여는 150초 이상 편은 낮았다. 비유하자면 이 계정은 같은 틀에 매번 다른 반죽을 붓는 붕어빵 가게다. 틀(템플릿)은 ContentsMaker의 V4.0(`news_v4`: 정지 이미지 + 전 구간 TTS + BGM 없음)과 골격이 거의 같아서, 새 파이프라인을 만들 필요가 없다. 바꿀 것은 다섯 가지다. 길이 캡을 62초에서 180초로 늘리고, 카테고리 차단을 풀고, 판화 화풍 프리셋을 추가하고, 크림 캔버스와 박스 없는 자막을 만들고, 정치 전용 게이트를 면제하는 것이다. 다만 측정 범위에 한계가 있다. 로그아웃 상태에서 볼 수 있는 **12편만** 분석했고, **조회수·저장·공유는 하나도 확보하지 못했다**. 그래서 성과 판단은 좋아요 기반의 약한 신호다. 구현하면 3개 이상의 파일을 고치게 되므로 프로젝트 규칙(HARD-GATE)에 따라 코딩 전에 `/plan` 승인을 먼저 받아야 한다.

## 이름과 달리 햄스터가 없는 1.6만 팔로워 지식 채널

계정명의 "햄스터"는 운영자 닉네임이다. 모든 영상 우하단에 `made by 햄스터` 워터마크가 붙는다. 바이오는 "낮엔 전략 기획, 밤엔 앱 개발. / 신기한 동물·생물·물리 이야기 좋아합니다"다 ([Instagram 프로필](https://www.instagram.com/hamster.743606/)). 이름만 보고 '정서불안 김햄찌' 같은 AI 동물 캐릭터 스킷으로 분류하기 쉽지만, 실제 영상에는 캐릭터도, 립싱크도, 의인화 스킷도 없다. 대본 화자도 무인칭 해설자다. "스탯·설계·밸런스" 같은 게임·기획 어휘로 동물을 평가하는 시선에 운영자 페르소나가 간접적으로 묻어날 뿐이다.

주제는 두 갈래다. 하나는 **최신 학술논문 1편을 썰로 푼 과학 이야기**로, 캡션에 `출처 : 저널, 논문 제목, 연도`를 단다. 오랑우탄 편은 PNAS 2026, 고래 이빨 편은 Frontiers in Marine Science 2026을 출처로 달았다. 다른 하나는 **사물·동물·취미를 "허당 설계"로 비꼬는 드립형 해설**이다(멧돼지, 제주도 낚시, 헬스장, 타짜 도박판). 캡션은 제목 한 줄이 전부이고 **해시태그는 12편 모두 0개**다 ([Reel DeYjONDgW7J](https://www.instagram.com/reel/DeYjONDgW7J/), [Reel DebH8AxgBcB](https://www.instagram.com/reel/DebH8AxgBcB/)).

업로드는 기계처럼 정확하다. 관측된 12편은 2.75일에 걸쳐 올라왔고(하루 약 4편), 업로드 시각은 **07:06 / 11:06 / 15:07 / 18:07 / 21:07 KST** 슬롯에 분 단위까지 맞아떨어진다. 이 속도를 91편까지 거꾸로 계산하면 시작점은 2026-09-21 전후다. 계정 개설일은 로그인해야 보이므로 이 값은 **추정**이다. 추정이 맞다면 약 3~4주 만에 1.6만 팔로워를 모은 셈이지만 검증되지 않았다. 좋아요 중앙값은 12편 전체 기준 **292**, 24시간 이상 지난 8편 기준 **384**다. 최고는 베이즈 정리 잠수함 편의 **961**(팔로워 대비 5.85%)이다 ([Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)).

| 편 | 길이(초) | 좋아요 | 댓글 | 유형 |
|---|---|---|---|---|
| [베이즈 잠수함](https://www.instagram.com/reel/DeZMeEIgyot/) | 120.5 | 961 | 30 | 논문(역사) |
| [오랑우탄](https://www.instagram.com/reel/DeYjONDgW7J/) | 99.0 | 816 | 34 | 논문(동물) |
| [제주도 낚시](https://www.instagram.com/reel/DeXsKpVAnP9/) | 134.5 | 674 | 64 | 취미 드립 |
| [멧돼지](https://www.instagram.com/reel/Dec1xpsAXZX/) (8시간 경과) | 128.9 | 589 | 50 | 동물 드립 |
| [고래 이빨](https://www.instagram.com/reel/DebH8AxgBcB/) | 123.9 | 470 | 8 | 논문 |
| [에니그마](https://www.instagram.com/reel/DeasgWygytS/) | 170.2 | 235 | 14 | 역사·기술 |
| [좀비 사고실험](https://www.instagram.com/reel/DebcmKDg06A/) | 147.4 | 140 | 11 | 철학 |
| [타짜 도박판](https://www.instagram.com/reel/DeY3zw6gxQ1/) | 155.3 | 83 | 9 | 취미 드립 |

데이터 한계도 분명하다. 로그아웃 그리드는 최근 12편만 노출하고, 다음 페이지 요청과 미러 사이트는 모두 차단됐다. 나머지 **79편, 조회수, 저장·공유 수, 하이라이트, 링크인바이오 URL**은 확보하지 못했다. 관측 시점의 경과 시간도 편마다 0.3~66시간으로 달라서, 위 좋아요는 정규화된 비교가 아니다. 79편과 조회수를 얻으려면 로그인 브라우저로 Reels 탭을 직접 열어야 한다.

## 정지 화면 20초와 3.5초 움직임이 만드는 2분 리듬

12편 모두 **720×1280, 30fps, -14.0 LUFS**이고 길이는 99~170초(중앙값 126.4초)다. 레이아웃은 1~2px 오차 안에서 고정된 템플릿이다. 배경은 크림 단색 `#F6EFE1`이다. 상단 중앙에 Black Han Sans 제목을 놓고 영상 내내 고정한다. 중앙에는 662×620 이미지 박스가 있고, 하단에는 Pretendard SemiBold로 2~3줄 검정 자막을 박스·테두리 없이 얹는다. 우하단에는 워터마크가 있다 ([Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/)). 제목은 글자 수 제한 때문에 문장 중간에서 잘린다("오랑우탄 엄마는 새끼의"). 자동 템플릿이 자른 것으로 보이는데, 결과적으로 호기심을 자극하는 미완결 제목이 됐다.

한 편은 **일러스트 7~9장(중앙값 8)**으로 구성된다. 커버 컷(3~7초)은 배경 없는 피사체 하나다. 이후 장은 장면 일러스트이고 장당 13~26초씩 정지해 있다. 전환은 페이드 없는 **하드컷**이다. 정지 화면에 생기를 주는 장치는 장마다 한 번 나오는 **약 3.5초의 "모션 버스트"**다. 서서히 1.08~1.15배로 밀고 들어가면서 멧돼지 다리나 파도 가장자리 같은 형태가 미세하게 변한다. 버스트 시작은 특정 자막 문장 시작과 **0.3초 안에서 97.5%(80개 중 78개)** 일치한다 ([Reel Dec1xpsAXZX](https://www.instagram.com/reel/Dec1xpsAXZX/)). 순수한 확대만으로는 설명되지 않는 비강체 변형이 있어서, 정지 이미지를 image-to-video 모델로 짧게 영상화한 클립으로 **추정**한다. 앞선 장르 노트는 "영상 생성이 없다"고 적었지만, 이후 프레임 단위 측정으로 이 버스트가 확인됐으므로 이 보고서는 측정 결과를 따른다. 코드 줌과 i2v를 완전히 구분하지는 못했다.

오디오는 **BGM과 효과음이 없다**. 챕터 경계마다 정확히 **0.40초의 디지털 무음(샘플값 0)**이 들어가는데, BGM이 깔려 있었다면 이런 무음이 나올 수 없다. 11편의 말 속도는 **한글 8.0~8.4음절/초**로 고정돼 있고 F0 중앙값은 약 210Hz로 여성 음역이다. 이런 신호들로 보아 **챕터 하나를 TTS 한 번 호출로 합성하고 0.4초 무음을 끼워 이어 붙인 구조**로 판단한다(추정, 근거는 강함). 일러스트 컷은 이 0.4초 무음의 한가운데에 떨어진다 ([Reel DeYjONDgW7J](https://www.instagram.com/reel/DeYjONDgW7J/), [Reel DeasgWygytS](https://www.instagram.com/reel/DeasgWygytS/)). 자막 큐 하나는 TTS 문장 또는 쉼표 절 하나에 대응하고, 큐 길이 중앙값은 3.1초다. 오탈자("헬스창", "유치으로")가 그대로 남아 있어 사람이 다시 손본 흔적은 없어 보인다.

대본은 **"일러스트 1장 = 챕터 1개 = 소주제 1개"** 구조다. 훅은 커버 컷 동안 단정형 한두 문장으로 끝낸다. 예를 들어 베이즈 편은 "1968년, 미국 핵잠수함 한 척이 대서양 한가운데서 감쪽같이 사라집니다"로 연다. 각 챕터는 "달리기 방식도 이상합니다." 같은 짧은 소제목형 문장으로 시작하고, 사실 3~5문장을 거쳐 게임·자동차 비유 펀치("코는 최첨단 레이더인데 모니터 해상도는 144p")로 닫는다. 결말은 "정리하면/결국" 요약에 아이러니 한 줄을 붙인다. 12편 OCR 대본 전체에서 "팔로우/구독/댓글/좋아요/여러분/저는"은 **0회**, 물음표는 2회뿐이다. **CTA 없이 끝난다**는 점이 ContentsMaker의 판정형 CTA와 가장 크게 다르다 ([Reel Dec1xpsAXZX](https://www.instagram.com/reel/Dec1xpsAXZX/)). 논문형도 대본 안에서는 "15년 동안 끈질기게 추적한 연구가 있습니다" 정도만 말하고, 저널명은 캡션에만 적는다.

## 짧고 구체적인 논문 썰이 좋아요를 두 배 받았다

포맷이 동일하므로 성과 차이는 대본에서 설명해야 한다. 21시간 이상 지난 9편에서 좋아요와 길이의 스피어만 상관은 **-0.63**, 좋아요와 글자 수도 **-0.63**이었다. 좋아요 470 이상인 상위 4편은 길이 중앙값이 **122.2초**(글자 1,056.5)였고, 하위 5편은 **147.4초**(1,258자)였다. 논문 출처를 단 4편의 좋아요 중앙값은 **643**, 출처 없는 24시간 이상 경과 4편은 **260.5**였다 ([Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/), [Reel DeY3zw6gxQ1](https://www.instagram.com/reel/DeY3zw6gxQ1/)).

훅도 갈렸다. 상위 편은 사건("1968년, 핵잠수함이 사라집니다"), 대상의 반전 캐릭터("독고다이이자 극I형 동물"), 역설("제일 무서운데 나사 빠진 구석")로 시작한다. 하위 편은 일반론("한국인에게 도박은 유구한 전통 놀이"), 우회 도입("넷플릭스 좀비 영화를 보면…"), 백과사전식 도입("2차 대전 당시 … 암호 기계가 있습니다")으로 시작한다. 하위 편에는 배경 설명 챕터가 2개 이상이고, 추상적(철학 좀비)이거나 비호감(도박 사기·욕설 인용)인 소재가 몰려 있다. 반응 유형도 다르다. 드립형은 댓글/좋아요 비율이 높고(타짜 10.8%, 제주 9.5%) 논문형은 낮다(고래 1.7%, 베이즈 3.1%). 논문형은 조용히 소비되고 드립형은 경험을 공유하게 만드는 것으로 보인다.

이 결론은 **표본 8~9편, 조회수 없는 좋아요 비교**에 근거한 약한 신호다. 논문형과 드립형 비교는 4 대 4라 인과를 확정할 수 없다. 2위 오랑우탄 편은 가장 짧고(99초) 말 속도도 가장 느리다(6.97음절/초). 그러니 "빠를수록 좋다"가 아니라 **"짧고 한 메시지"**가 유리하다는 가설을 지지할 뿐이다. ContentsMaker 채널의 039 실측("편차를 만드는 건 제작 품질이 아니라 소재 조건")과 같은 구조라는 점은 눈여겨볼 만하다.

## 재현 레시피 (1080×1920, 측정값 ×1.5 환산)

아래 수치는 12편 실측을 1080 기준으로 환산했다. "(추정)" 표시 외에는 측정에서 나온 값이다 ([Reel DeZMeEIgyot](https://www.instagram.com/reel/DeZMeEIgyot/), [Reel Dec1xpsAXZX](https://www.instagram.com/reel/Dec1xpsAXZX/), [Reel DeYjONDgW7J](https://www.instagram.com/reel/DeYjONDgW7J/)).

| 항목 | 스펙 |
|---|---|
| 캔버스 | 1080×1920, 30fps, 단색 `#F6EFE1`(대체 `#F5ECDF`) |
| 제목 | Black Han Sans 약 84px, `#111`, 가로 중앙, 1줄 글리프 y 213~290, 최대 폭 약 900px(넘치면 2줄), 영상 내내 고정, 박스·테두리 없음 |
| 이미지 박스 | x 42~1034, y 366~1295(993×930), overflow hidden. 3:2·4:3 이미지는 가로 993에 맞춰 세로 중앙 배치(추정) |
| 자막 | Pretendard SemiBold 약 57px, line-height 1.2, `#120E0A`, 중앙정렬, **첫 줄 상단 y≈1338 고정(아래로 늘어남)**, 폭 약 900px 자동 줄바꿈, 최대 3줄, 박스·그림자 없음 |
| 워터마크 | `made by {채널명}` 우하단(오른쪽 끝 x≈1041, y 1863~1890) |
| 전환 | 이미지·자막 모두 하드컷 |
| 일러스트 | 8장 = 커버 컷아웃 1 + 챕터 장면 7 |
| 컷 길이 | 커버 3~7초(첫 1~2문장) · 1장 7~14초 · 본문 17~24초 · 마지막 14~18초 |
| 모션 | 커버는 정지. 챕터마다 약 3.5초 푸시인(1.0→1.10, ease-in-out, 박스 안 클리핑)을 그 장면을 묘사하는 문장 시작에 맞춰 1회 재생하고, 앞뒤는 정지. i2v가 없으면 코드 줌으로 대체 가능(추정) |
| 나레이션 | 여성 음역 TTS, 약 8.2음절/초, "~니다" 존댓말. **챕터 단위로 TTS 호출**, 챕터 사이 0.40초 무음, 시작 0.2초·끝 0.75초 무음 |
| 자막 단위 | TTS 문장 또는 쉼표 절 1개 = 큐 1개, 1.5~4.5초(중앙 3.1), 큐당 약 24~31자 |
| BGM / SFX | 없음 / 없음 |
| 라우드니스 | -14 LUFS |
| 길이 | **99~135초 권장**(상위 편 범위). 150초 이상은 하위 편에만 있음 |
| 캡션 | 제목 1줄(+논문형은 `출처 : 저널, 논문 제목, 연도`), 해시태그 0 |

대본은 약 120초, 1,000~1,100자, 8챕터를 기준으로 다음 순서를 따른다. **0번 커버(0~4초)**: 질문형·인사 없이 사건·숫자("1968년, ~가 사라집니다")나 대상의 역설("~인데, ~한 구석이 한둘이 아닙니다")을 1~2문장으로 던진다. **1번 도입(4~15초)**: 상황과 스케일을 2~4문장으로 깔고 "그런데/근데"로 반전을 예고한다. **2~6번 본문(장당 약 18초)**: 짧은 소제목형 문장 → 사실 3~5문장 → 생활·게임 비유 펀치 1문장 순서다. 논문형은 2~3장에 "~를 N년 추적한 연구가 있습니다" 한 줄만 넣는다. **7번 결론**: "정리하면/결국" 요약 뒤에 아이러니나 교훈 펀치라인으로 끝내고 CTA는 넣지 않는다.

일러스트 프롬프트(영문) 초안은 다음과 같다. 장면 장: `Vintage mid-century print illustration of {핵심 문장 1개의 장면}. Fine engraving-style cross-hatching and stipple shading, slightly grainy risograph texture, limited palette of deep prussian navy, mustard ochre, burnt orange, olive green and warm cream, small red accents only for emphasis. Organic irregular vignette dissolving into a plain warm cream background (#F5EEE0). No text, no letters, no numbers, no watermark. Aspect 1:1.` 커버 장은 같은 화풍으로 `Single {피사체} isolated on a plain warm cream background, no scenery, full body, centered`라고 쓴다. 판화풍 세트의 일관성은 해칭·잉크 워시·세피아 톤 같은 기술 키워드를 모든 장에 똑같이 반복하는 방식으로 잡는 것이 업계 관행이다 ([Morphic](https://morphic.com/resources/images/victorian-engraving-image)). 같은 편 안에서 주인공(멧돼지, 에니그마 기계)의 외형이 유지되므로, 커버 이미지를 이후 장의 레퍼런스로 넣는 운영 방식으로 추정한다.

## 장르는 검증됐지만, 이 포맷은 슬라이드쇼 정책선에 서 있다

한국에서 이 장르는 '지식튜브'나 '지식 스토리텔링'으로 불린다. 사피엔스 스튜디오(구독 77만), 김성회의 G식백과(65만) 같은 롱폼이 이미 자리를 잡았다 ([더팩트](https://news.tf.co.kr/read/ogmeta/1874011.htm)). 숏폼 쪽에서는 지식코리야가 가정형 과학 쇼츠로 두 달 만에 구독 1만에서 54만으로 늘었다 ([캐릿](https://www.careet.net/1294)). 반면 **"논문 1편을 2분 썰로 풀고 출처를 다는" 형태의 대형 한국 사례는 찾지 못했다**. 빈 자리일 수도 있고 검증되지 않은 자리일 수도 있다. 길이 측면에서는 Instagram이 2025년 1월 릴스 상한을 3분으로 늘렸고 ([Buffer](https://buffer.com/resources/instagram-reels-length)), Mosseri는 시청 시간과 도달 대비 DM 공유를 핵심 신호로 꼽았다 ([Lindsey Gamble](https://lindseygamble.com/blog/instagram-reveals-how-its-algorithm-weighs-watch-time-for-reels)). 끝까지 보면 시청 초가 길고 "이거 봐" 공유 동기가 있는 2분 논문 썰에 유리한 구조다. 다만 2분 릴스와 60초 릴스를 비교한 1차 데이터는 없다.

리스크는 세 겹이다. **첫째, YouTube 불성실 콘텐츠 정책.** 2025-07-15 개정의 수익화 불가 예시에는 "이미지 슬라이드쇼", "추가 논평이 거의 없는 자동 낭독", "모두 같은 내레이션을 쓰는 슬라이드쇼 채널"이 들어 있다 ([YouTube 고객센터](https://support.google.com/youtube/answer/1311392?hl=en)). 2026년 1월에는 대규모 집행이 보고됐다 ([Tubefilter](https://tubefilter.com/2026/01/29/youtube-ai-slop-channel-crackdown-bans/)). 하루 4편, 같은 목소리, 같은 템플릿은 겉모양이 이 예시와 겹친다. 방어 근거는 편마다 다른 소재, 고유 해석(드립·비유), 출처 명시다. 판정 축은 편수가 아니라 **"표면적 차이만 있는가"**다. 단, 이 정책 문구는 검색 스니펫과 2차 출처로 재확인한 것이고 **원문은 확인하지 못했으므로 검증이 필요하다**. 수익화 판정은 채널 단위로 내려지므로, 기존 시사 채널에 섞으면 그 채널까지 위험해진다.

**둘째, 정확성.** Peters & Chin-Yee(2025)는 LLM 10종의 과학 요약 4,900건을 원문과 비교했다. LLM 요약은 사람 요약보다 과일반화 가능성이 **약 5배** 높았고, "정확하게 하라"고 지시하면 오히려 약 2배 더 과일반화했다 ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12042776/)). "논문 PDF → LLM 요약 → 썰"을 자동화하면 "쥐 실험 → 사람에게도", "상관 → 인과" 오류가 체계적으로 섞여 들어간다. 대상 계정에도 지방간·미토콘드리아 같은 의학 편이 있다. 건강 소재는 YouTube 의료 오정보 정책에도 걸리므로 초기 소재에서 빼는 편이 안전하다.

**셋째, 저작권과 AI 라벨.** 논문 속 사실과 아이디어는 자유롭게 쓸 수 있지만, **논문의 문장과 도표(figure)는 보호된다** ([Muskulus, Copyright for Scientists](https://muskulus.folk.ntnu.no/blog/copyright-for-scientists/)). V4.0처럼 "캡처 + credit" 방식으로 논문 도표를 붙이면 출처 표기만으로는 이용 허락이 되지 않는다. 일러스트는 새로 그리고 논문은 인용 표기만 하는 대상 계정의 방식이 가장 안전하다. 라벨 쪽을 보면, YouTube 합성 콘텐츠 공개 의무는 실제로 착각할 수 있는 콘텐츠에만 적용되고 명백히 비현실적인 애니메이션은 제외된다 ([YouTube 고객센터](https://support.google.com/youtube/answer/14328491)). TikTok도 사실적인 AIGC에 라벨을 의무화한다 ([TikTok 뉴스룸](https://newsroom.tiktok.com/more-ways-to-spot-shape-and-understand-ai-content?lang=en)). 판화 일러스트는 의무 대상 밖일 가능성이 높지만, **사람처럼 들리는 TTS가 "realistic audio"에 해당하는지는 원문을 확인하지 못했다**. 그러니 자발적 AI 고지가 가장 안전하다. 한국 AI 기본법(2026-01-22 시행)의 표시 의무는 AI 서비스 사업자에게 있고, 도구로 쓰는 창작자는 대상이 아니다 ([뉴시스](https://www.newsis.com/view/NISX20260121_0003485509)).

## ContentsMaker 구현: V4.0을 복제해 `knowledge_v6`로 격리한다

가장 작은 변경 경로는 V4.0 렌더러를 복제한 새 포맷 키(가칭 `knowledge_v6`)다. 기존 V4.0 동작과 정치 게이트는 그대로 두고 `format`·`category`·`source_type` 축으로 격리한다. 041~043이 써 온 방식과 같다. 아래 경로와 상수는 2026-10-14 작업 트리에서 직접 확인했다.

| 재사용 요소 | 위치 | 쓰는 방식 |
|---|---|---|
| 사진 트랙 타이머 | `scripts/news_v4_timeline.py` `photo_schedule()`, `DEFAULT_INTERVAL_MS = 3400` | 3.4초 고정 대신 사진별 `dur`(13~22초) 지정. 또는 챕터(TTS 덩어리) 경계로 맞추는 모드 추가 |
| 자막 분할 | 같은 파일 `split_caption()`, `DEFAULT_CAPTION_CHARS = 16` | 16자 1줄 → 문장·쉼표 절 단위 2~3줄 큐로 바꿈 |
| TTS·재사용 | `scripts/render_news_v4.py` `_tts_raw()` / `_synthesize()`, `--reuse-tts` | 음성은 Kore(여성), style_prompt는 이야기꾼 톤으로 교체 |
| BGM 고정 OFF | `render_news_v4.py` `USE_BGM = False` | 그대로 사용 |
| 출처 게이트 | `_gate_fact_sources`(원본 `scripts/render_profile_v3.py`), 나무위키 차단 | 논문 DOI/URL을 `fact_sources`로 필수화 |
| 밝은 캔버스 렌더 | `render_video(... respect_background_colors=True, overlay_boxes=False, headline_plain=True)` | `bg_colors`를 `#F6EFE1`로 |
| Remotion 레이어 | `src/video/remotion/src/components/NewsCardLayer.tsx` | 1080 정사각 박스 + 줌 재사용 |
| 텍스트 금지 가드 | `src/illustrator/image_constants.py` `NO_TEXT_GUARD` | 그대로. 사진용 `PHOTO_STYLE_PREFIX/FOOTER`는 쓰지 않음 |

바꿔야 할 지점은 다음과 같다. ① **길이 캡**: `scripts/political_length.py`의 `TARGET_MAX_SEC = 62.0`이 기본이고, `max_final_sec()`는 `FormatRules.max_final_sec`를 우선한다(V5만 70초). 새 `FormatRules`에 `max_final_sec=180.0`을 넣으면 해결된다. 운영 권장은 135초 이하다. ② **카테고리 3중 차단**: `render_news_v4.py`의 `ALLOWED_CATEGORIES = (POLITICAL, "entertainment", "society")`, `scripts/shorts_category.py`의 `CATEGORIES`, `scripts/shorts_domain.py`의 `rules_for()`가 모두 ValueError를 낸다. `science`(또는 `knowledge`)를 추가하거나 새 렌더러에서 우회해야 한다. ③ **정치 게이트 상속**: V4.0의 `load_config()`는 `political_cta.apply_cta`를 적용하고, `config_warnings()`는 035 CTA·039 돌파·040 대칭 경고를 재사용한다. 새 `FormatRules`(`scripts/shorts_format.py`)에서 `symmetry_applies=False`와 CTA 면제(무CTA 스타일)를 설정해야 한다. ④ **source_type**: `render_news_v4.py`에 `source_type="political_pro"`가 박혀 있다. 이걸 그대로 쓰면 `src/tts/voice_config.py`의 `DARK_BGM_SOURCE_TYPES`와 업로드 통계에서 정치로 섞이므로 `knowledge`로 분리한다. ⑤ **자막 스타일**: `NewsCardLayer.tsx`는 검은 반투명 박스(`rgba(0,0,0,0.88)`) + 흰 글자다. "크림 위 검정 글자, 박스 없음, 상단 고정 2~3줄" 옵트인 프롭을 추가하되, 042/043 관행대로 **미지정 시 기존 still 바이트 동일**을 검증한다. ⑥ **일러스트 프리셋**: `src/illustrator/prompt_builder.py`의 `IMAGE_STYLE_PRESETS`는 webtoon/3d_pixar/realistic/anime 4종뿐이므로 `vintage_engraving`을 추가한다. 레퍼런스 이미지는 `image_generator.py`가 webtoon 외에는 끄고, `gemini_web_image_gen.py`는 "(9:16 세로)"를 하드코딩하므로 1:1 생성 경로를 손봐야 한다. ⑦ **V4.0 사진 전제**: `MIN_PHOTOS = 4`, `photos[*].credit` 필수 규칙은 일러스트에 맞게 "AI 생성" 고정값으로 바꾼다.

TTS 호출 구조는 대상 계정을 따르는 편이 낫다. 레포의 Gemini TTS는 대본 전체를 1회 호출로 합성한다. 2분 대본(약 930~1,100자)은 요청당 5,000자 한도 안이지만 ([Google Cloud Gemini-TTS](https://cloud.google.com/text-to-speech/docs/gemini-tts)), 문장 사이 무음이 거의 없는 연속 나레이션에서는 `align_timings_to_silence`의 앵커가 줄어든다. 길어진 대본은 런어웨이(무음 삽입으로 수백 초가 되는 현상) 확률도 높인다. **챕터 단위로 호출하고 0.4초 무음으로 잇는 방식**은 대상 계정의 구조를 재현하는 동시에 이 두 위험을 줄이고, 챕터 경계 = 일러스트 컷 타이밍도 공짜로 준다. 다만 호출 수가 편당 7~8회로 늘어 Gemini 무료 일일 한도(약 10회)와 충돌한다. 그래서 유료 키나 다른 TTS가 필요하다는 점을 계획 단계에서 정해야 한다. 3.5초 모션 버스트는 1단계에서는 Remotion 코드 줌으로 대체한다. i2v(`src/video_gen/`)는 Freepik 구독이 유효한지 확인한 뒤 2단계로 미룬다.

새 렌더러(`scripts/render_knowledge_v6.py`), 템플릿(`scripts/political_v2_configs/_template_knowledge_v6.json`), `shorts_format.py`, `shorts_category.py`, `shorts_domain.py`, `NewsCardLayer.tsx`, `prompt_builder.py`까지 최소 7개 파일을 건드리게 된다. CLAUDE.md HARD-GATE(새 기능·3개 이상 파일)에 해당하므로 **코딩 전에 `/plan`으로 계획을 승인받아야 한다**. 계획에는 별도 계정 여부와 Instagram 업로더 부재 처리(`src/upload/`에는 YouTube·TikTok만 있다)도 포함해야 한다. Instagram Graph API 게시 한도는 24시간 50건이다 ([Meta 개발자 문서](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing)).

## Conclusion

이 계정에서 배울 것은 화려한 AI 영상 기술이 아니다. **고정 템플릿 하나로 하루 4편을 찍어내면서 성과는 대본으로만 가르는 운영 구조**다. 이는 ContentsMaker 채널이 039에서 실측한 결론("편차는 제작이 아니라 소재")과 같은 방향이다. 그래서 새 포맷의 투자는 렌더러보다 **소재원(신규 논문 피드)과 대본 규칙(사건·숫자 훅, 120초, 비유 펀치, 과일반화 대조 체크)**에 실려야 한다. 정치·건강을 제외한 동물·과학사 논문으로 시작하는 것이 정책·정확성 리스크가 가장 낮은 출발점이다.

채널 전략은 분리가 맞다. 2분 길이, CTA 없는 교양 톤, 하루 4편 물량은 모두 현재 YouTube 시사 채널의 측정 체계(036 원장, 040 편성, 044 추천기)와 수익화 심사를 흔든다. 벤치마크의 근거도 Instagram에서 나왔다. **별도 Instagram 계정에서 8~10편 파일럿을 돌리고, 조회수가 보이는 로그인 상태에서 대상 계정의 나머지 79편을 재측정한 뒤 판정**하는 순서가 041 V3.0 판정법과 일관된다. 지금 가진 근거는 12편의 좋아요뿐이다.
