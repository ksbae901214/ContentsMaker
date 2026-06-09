"""정치쇼츠 V3 — @김정치입니다 격리 모드 패키지.

기존 V1(political) / V2(political_pro) 파이프라인과 물리적으로 격리된 독립 패키지.
기존 모듈은 read-only import만 허용한다 (편집 X).

Lock-in (사용자 명시, 2026-06-05):
- TTS: ko-KR-InJoonNeural +22% (V1 락인)
- 워터마크: 제외
- 레이아웃: normal / vs_card / grid_2x2 / data_card 4종
- 효과음(SFX): 영구 0
- 씬 전환 효과: 영구 0 (하드 컷)
- TTS 씬 간 gap: 300 ms 고정
- 영상 추출: Gemini Files API → Claude 검색 키워드 → yt-dlp 3단계

진입점: python3 -m src.jpolitics.main / /jpolitics Next.js 라우트
"""
