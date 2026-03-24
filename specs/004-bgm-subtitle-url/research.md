# Research: BGM + 자막 줄바꿈 + URL 소스 확장

## R1: BGM 볼륨 믹싱

**Decision**: Remotion `<Audio volume={0.15}>` 사용
**Rationale**: Remotion의 Audio 컴포넌트가 volume prop을 0~1로 지원. TTS는 1.0, BGM은 0.15로 설정하면 TTS가 묻히지 않음.
**Alternatives**: FFmpeg 후처리로 믹싱 → 불필요한 복잡도, Remotion 자체 기능으로 충분

## R2: 로열티프리 BGM 소스

**Decision**: Pixabay Music (https://pixabay.com/music/)
**Rationale**: 상업적 무료, 크레딧 불필요, MP3 직접 다운로드 가능, 품질 양호
**Alternatives**:
- YouTube Audio Library → 다운로드 제한, API 없음
- Free Music Archive → 라이선스 복잡
- Uppbeat → 무료 플랜 제한적

## R3: 디시인사이드 HTML 구조

**Decision**: Playwright로 페이지 렌더링 후 CSS 선택자 파싱
**Rationale**: 디시인사이드는 동적 로딩 없이 서버 렌더링이지만, 일부 갤러리는 JS 필요. Playwright가 가장 안정적.
**핵심 선택자**:
- 제목: `.title_subject` 또는 `h3.title span.title_subject`
- 본문: `.writing_view_box` 또는 `div.write_div`
- 댓글: `.cmt_txtbox` (각 댓글), `.btn_cmt_up` (좋아요 수)
**Alternatives**: requests + BeautifulSoup → 일부 갤러리에서 JS 필요한 콘텐츠 누락

## R4: 네이트판 HTML 구조

**Decision**: Playwright + CSS 선택자 파싱
**핵심 선택자**:
- 제목: `h3.aTitle`
- 본문: `#contentArea` 또는 `div#contentArea`
- 댓글: `.cmt_list .txt` (각 댓글)
**Rationale**: 네이트판은 비교적 단순한 HTML 구조로 파싱 용이

## R5: 네이버 카페 HTML 구조

**Decision**: Playwright + iframe 내부 접근
**Rationale**: 네이버 카페 게시글은 iframe 안에 콘텐츠가 렌더링됨. Playwright로 iframe에 접근하여 파싱 필요.
**핵심 선택자** (iframe 내부):
- 제목: `.ArticleTitle` 또는 `h3.title_text`
- 본문: `.article_viewer` 또는 `div.se-main-container`
- 댓글: `.comment_text_box` (각 댓글)
**제한사항**: 비공개 카페/게시글은 로그인 필요 → "접근 불가" 오류 반환
**Alternatives**: 네이버 API → 카페 API는 2024년 종료, 직접 파싱만 가능

## R6: 자막 줄바꿈 전략

**Decision**: Claude Code 분석 프롬프트에 줄바꿈 규칙 추가 + 후처리 폴백
**Rationale**: AI가 문맥을 이해하고 자연스러운 위치에서 줄바꿈. 만약 AI가 줄바꿈을 누락하면 Python 후처리로 15자 단위 강제 줄바꿈.
**줄바꿈 규칙**:
1. 1줄 최대 15자
2. 조사 뒤 (은/는/이/가/을/를/에/에서/도/만)
3. 쉼표/마침표 뒤
4. 의미 단위 (주어-서술어 경계)
**Alternatives**: 순수 Python 규칙 기반 → 문맥 무시하여 어색한 줄바꿈 발생

## R7: 키워드 하이라이트 구현

**Decision**: AI 분석 시 `highlight_words` 배열 추가 → SceneText에서 해당 단어를 감정 색상으로 렌더링
**Rationale**: 씬 데이터에 하이라이트 대상 단어를 포함시키면 Remotion에서 단순 문자열 매칭으로 색상 적용 가능
**감정별 색상**:
- funny: `#FFD700` (금색/노랑)
- touching: `#FF69B4` (분홍)
- angry: `#FF4444` (빨강)
- relatable: `#87CEEB` (하늘색)
