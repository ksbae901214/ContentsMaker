# Quickstart: 006-video-shorts-mode

## 개발 환경 준비

```bash
# Python 의존성
pip install -r requirements.txt    # httpx 추가됨

# Node 의존성 (Remotion)
cd src/video/remotion && npm install && cd ../../..

# 환경 변수
export OPENAI_API_KEY="..."         # 이미지 생성 (기존)
export SEEDANCE_API_KEY="..."       # 영상 생성 (선택, P2 기능)
```

## 구현 순서

```
Phase 6-1: TopicInput 모델 + analyze_topic() — API 키 불필요
Phase 6-2: IMAGE_STYLE_PRESETS + 프롬프트 분기 — API 키 불필요
Phase 6-3: Seedance API 완전 구현 — SEEDANCE_API_KEY 필요
Phase 6-4: route.ts + renderer.py 파이프라인 분기
Phase 6-5: UI 업데이트 (토글, 스타일 선택, 주제 탭)
Phase 6-6: 테스트 작성 + E2E 검증
```

## 주요 수정 파일

| 파일 | 변경 | 의존성 |
|------|------|--------|
| `src/scraper/topic_input.py` | **신규** | 없음 |
| `src/analyzer/prompt_template.py` | TOPIC_ANALYZE_PROMPT 추가 | 없음 |
| `src/analyzer/claude_analyzer.py` | analyze_topic() 추가 | topic_input, prompt_template |
| `src/analyzer/script_models.py` | Metadata.source_type 추가 | 없음 |
| `src/illustrator/prompt_builder.py` | IMAGE_STYLE_PRESETS, image_style 파라미터 | 없음 |
| `src/illustrator/image_generator.py` | image_style 파라미터 전달 | prompt_builder |
| `src/video_gen/seedance_gen.py` | TODO 구현 완성 | httpx |
| `src/video_gen/base.py` | generate_and_wait() 추가 | 없음 |
| `src/video/renderer.py` | scene_videos 파라미터 + public/ 복사 | 없음 |
| `app/api/generate/route.ts` | topic 모드 + visualMode 분기 | Python 모듈 |
| `app/page.tsx` | 모드 토글, 스타일 선택, 주제 탭 | route.ts |

## 테스트 실행

```bash
# 전체 테스트
python3 -m pytest tests/ -v

# Phase 6 관련 테스트
python3 -m pytest tests/test_topic_input.py tests/test_prompt_template_topic.py tests/test_analyzer_topic.py -v

# 테스트 영상 생성 (이미지 제외)
python3 -m src.main manual --file data/raw/sample.json --no-images
```

## Constitution 체크포인트

- **원칙 I**: Seedance는 선택적(opt-in). 기본값은 이미지 모드 ($0.03/영상 유지)
- **원칙 II**: JSON 계약 유지. topic 모드도 동일한 ShortsScript 출력
- **원칙 III**: AI 영상 클립은 배경 역할. 텍스트 오버레이 유지
- **원칙 VI**: TopicInput은 frozen dataclass. 모듈 독립성 유지
- **원칙 VII**: 작업 완료 시 테스트 영상 생성 필수
- **원칙 VIII**: 전체 테스트 통과 후 커밋
