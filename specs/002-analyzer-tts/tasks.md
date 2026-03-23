# Tasks: Analyzer + TTS Module

**Input**: Design documents from `/specs/002-analyzer-tts/`
**Prerequisites**: plan.md, spec.md, Phase 1 완료 (models.py, validator.py, settings.py)

**Organization**: Analyzer(P1) → TTS(P1) → 통합(P2) 순서.

---

## Phase 1: Setup

- [ ] T001 디렉토리 생성: `src/analyzer/`, `src/tts/`, `data/scripts/`, `data/audio/`
- [ ] T002 requirements.txt 업데이트: `edge-tts`, `pytest-asyncio` 추가
- [ ] T003 settings.py 업데이트: DATA_SCRIPTS_DIR, DATA_AUDIO_DIR 경로 추가

---

## Phase 2: Foundational — ShortsScript 데이터 모델

- [ ] T004 ShortsScript, Scene, Metadata, AudioConfig, BackgroundConfig 데이터 클래스 in `src/analyzer/script_models.py`
- [ ] T005 ShortsScript 직렬화/역직렬화 + JSON 저장/로드 in `src/analyzer/script_models.py`
- [ ] T006 ShortsScript 검증기 in `src/analyzer/script_validator.py` (필수 필드, 씬 개수, duration 범위)
- [ ] T007 감정별 음성 설정 in `src/tts/voice_config.py` (VOICE_CONFIG dict)
- [ ] T008 [P] 데이터 모델 테스트 in `tests/test_script_models.py`

**Checkpoint**: `python3 -m pytest tests/test_script_models.py -v`

---

## Phase 3: User Story 1 — Analyzer (Claude Code → script.json)

- [ ] T009 [US1] 프롬프트 템플릿 작성 in `src/analyzer/prompt_template.py` — 감정 분석 + 요약 + 타임라인 + 개인정보 마스킹
- [ ] T010 [US1] Claude Code 호출기 구현 in `src/analyzer/claude_analyzer.py` — subprocess로 `claude -p` 실행 + JSON 파싱
- [ ] T011 [US1] Analyzer 에러 처리 — Claude Code 실패, JSON 파싱 실패, 타임아웃
- [ ] T012 [US1] CLI에 analyze 서브커맨드 추가 in `src/main.py`
- [ ] T013 [US1] Analyzer 테스트 in `tests/test_analyzer.py` — 프롬프트 생성, JSON 파싱, 에러 처리 (Claude 호출은 mock)

**Checkpoint**: `python3 -m src.main analyze --file data/raw/sample.json` → `data/scripts/` 저장

---

## Phase 4: User Story 2 — TTS (script.json → voice.mp3)

- [ ] T014 [US2] edge-tts 래퍼 구현 in `src/tts/edge_tts_generator.py` — script.json 읽기 → 감정별 설정 → MP3 생성
- [ ] T015 [US2] TTS 에러 처리 — 네트워크 실패, 빈 스크립트, 파일 저장 실패
- [ ] T016 [US2] CLI에 tts 서브커맨드 추가 in `src/main.py`
- [ ] T017 [US2] TTS 테스트 in `tests/test_tts.py` — 음성 설정 선택, 에러 처리 (실제 TTS는 통합 테스트)

**Checkpoint**: `python3 -m src.main tts --file data/scripts/sample.json` → `data/audio/` 저장

---

## Phase 5: User Story 3 — 통합 (raw → script → voice)

- [ ] T018 [US3] analyze 서브커맨드에 `--with-tts` 옵션 추가 in `src/main.py`
- [ ] T019 [US3] 통합 테스트 in `tests/test_pipeline_analyze.py` — raw → script → voice 연속 실행

**Checkpoint**: `python3 -m src.main analyze --file data/raw/sample.json --with-tts`

---

## Phase 6: Polish

- [ ] T020 [P] 로깅 추가 in `src/analyzer/`, `src/tts/`
- [ ] T021 전체 테스트: `python3 -m pytest tests/ -v`
- [ ] T022 4종 감정 샘플로 end-to-end 검증 (funny, touching, angry, relatable)

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Models) → Phase 3 (Analyzer, US1)
                                    → Phase 4 (TTS, US2)
                                    → Phase 5 (통합, US3)
                                    → Phase 6 (Polish)
```

Phase 3과 4는 독립적이므로 병렬 가능 (다른 파일).

## Summary

| Phase | 태스크 수 | 핵심 산출물 |
|-------|----------|------------|
| Phase 1 Setup | 3개 | 디렉토리, 의존성 |
| Phase 2 Foundation | 5개 | script_models.py, voice_config.py |
| Phase 3 Analyzer | 5개 | claude_analyzer.py, prompt_template.py |
| Phase 4 TTS | 4개 | edge_tts_generator.py |
| Phase 5 Integration | 2개 | --with-tts 옵션 |
| Phase 6 Polish | 3개 | 로깅, 검증 |
| **Total** | **22개** | |
