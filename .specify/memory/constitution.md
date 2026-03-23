<!--
  Sync Impact Report
  Version change: 0.0.0 → 1.0.0 (initial ratification)
  Added principles: I–VII (all new)
  Added sections: Quality Gates, Technical Standards, Development Workflow, Governance
  Templates requiring updates:
    ✅ plan-template.md — Constitution Check section aligns with 7 principles
    ✅ spec-template.md — No structural change needed
    ✅ tasks-template.md — No structural change needed
  Follow-up TODOs: none
-->

# ContentsMaker Constitution

## Core Principles

### I. Zero-Cost Pipeline (무료 파이프라인 최우선)

모든 기능은 **API 비용 $0**으로 동작해야 한다. 유료 API 도입은 무료 대안이 없음을 증명한 후에만 허용한다.

- AI 분석: Claude Code (Sonnet 4.6) 직접 사용 — 별도 API 키 비용 없음
- TTS: edge-tts (Microsoft Edge 무료 엔진) MUST 사용 — 유료 TTS 금지
- 영상 렌더링: Remotion 로컬 렌더링 — Lambda는 Phase 3 이후 선택
- 배경: CSS 그라데이션 또는 Pexels 무료 스톡 — 유료 AI 영상 생성 금지 (Phase 1-2)
- 새 외부 서비스 도입 시 MUST 비용 정당화 문서 작성

**근거**: 콘텐츠 제작 도구의 수익성은 운영비 최소화에서 결정된다. 무료 도구로 충분한 품질을 달성할 수 있다면 유료 도구는 불필요한 비용이다.

### II. Pipeline Integrity (파이프라인 무결성)

각 단계의 입출력은 **JSON 계약**으로 명확히 정의되어야 하며, 한 단계의 실패가 전체 파이프라인을 중단시켜서는 안 된다.

- 5단계 파이프라인: Scraper → Analyzer → TTS → Video → Upload
- 각 단계는 **독립 실행 가능** (이전 단계의 출력 파일을 직접 입력으로 사용 가능)
- 단계 간 데이터 교환: JSON 파일 (`data/raw/`, `data/scripts/`, `data/audio/`, `data/outputs/`)
- 한 단계 실패 시: 에러 로그 + 해당 콘텐츠 스킵 → 다음 콘텐츠로 진행
- 중간 산출물 MUST 보존 (재실행 시 실패 단계부터 재시작 가능)

**근거**: 크롤링 실패, TTS 오류, 렌더링 충돌 등 각 단계마다 독립적인 장애 가능성이 있다. 파이프라인 한 곳의 실패가 전체를 멈추면 자동화의 의미가 사라진다.

### III. Text-First Video (텍스트 중심 영상)

쇼츠 영상의 주인공은 **텍스트**다. 배경, 음악, 효과는 텍스트 가독성을 보조하는 역할이다.

- 텍스트 가독성: 화면 너비의 80% 이내, 최소 font-size 32px, 흰색 텍스트 + 그림자 필수
- 배경: 텍스트를 방해하지 않는 단순 배경 (그라데이션, 블러 처리된 스톡 영상)
- 감정별 스타일: 4종 감정 테마 (funny/touching/angry/relatable) — 색상, 폰트 크기, 애니메이션 차별화
- 자막: 음성과 동기화된 자막 MUST 포함 (접근성 + 무음 시청자 고려)
- 영상 길이: 30–60초 (1분 초과 금지)
- 해상도: 1080x1920 (9:16 세로), 30fps

**근거**: 블라인드 쇼츠의 본질은 "익명 직장인의 생생한 이야기"다. 화려한 영상 효과보다 텍스트 전달력이 조회수와 참여율을 결정한다.

### IV. Content Safety & Legal Compliance (콘텐츠 안전 & 법적 준수)

모든 콘텐츠 MUST 법적 리스크와 커뮤니티 가이드를 사전에 필터링한다.

- 개인정보 마스킹: 실명, 직급, 구체적 부서명 등 식별 가능 정보 MUST 제거 또는 마스킹
- 부적절 콘텐츠 필터링: 욕설, 비속어, 성적 표현, 정치적 논란, 불법 행위 언급 → 자동 스킵
- 출처 명시: 영상 설명란에 "블라인드 커뮤니티 인기글 기반" 문구 MUST 포함
- 저작권: Fair Use 원칙 준수 — 원문 그대로 사용 금지, 요약/편집/해설 형태로 변환
- YouTube 가이드: AI 생성 콘텐츠 명시, 커뮤니티 가이드 준수
- 크롤링 윤리: 요청 간격 5초 이상, robots.txt 준수, 서버 부하 최소화

**근거**: 법적 문제 1건이 채널 전체를 폐쇄시킬 수 있다. 콘텐츠 안전은 성장보다 우선한다.

### V. Emotion-Driven Experience (감정 기반 경험)

모든 영상은 **감정 타입을 분석**하여 시각/청각 요소를 자동 최적화한다.

- 4종 감정: `funny` (재밌음), `touching` (감동), `angry` (분노), `relatable` (공감)
- 감정별 음성: edge-tts 한국어 음성 + 속도/피치 자동 조절
  - funny: `ko-KR-BongJinNeural` (+15% 속도, +5Hz 피치)
  - touching: `ko-KR-SunHiNeural` (-10% 속도, -3Hz 피치)
  - angry: `ko-KR-InJoonNeural` (+5% 속도, -10Hz 피치)
  - relatable: `ko-KR-SeoHyeonNeural` (기본값)
- 감정별 배경: 색상 그라데이션 차별화 (노랑/보라/빨강/파랑 계열)
- 감정별 BGM: 배경음악 자동 매칭 (Phase 2)
- 감정별 애니메이션: 텍스트 등장 효과 차별화 (bounce/fade/shake/slide)

**근거**: 동일한 텍스트라도 감정에 맞는 연출이 시청 유지율을 2-3배 높인다. 감정 분석 자동화는 대량 생산의 핵심이다.

### VI. Modularity & Immutability (모듈성 & 불변성)

코드 MUST 작은 단위로 분리하고, 데이터는 절대 변이(mutation)하지 않는다.

- 파일 크기: 400줄 초과 시 분리 검토, 800줄 한계
- 함수 크기: 50줄 이내
- 중첩: 4단계 이내
- 불변성: spread operator로 새 객체 생성, 원본 수정 금지
- 모듈 독립성: 각 모듈(scraper, analyzer, tts, video, upload)은 독립 실행/테스트 가능
- 설정 중앙화: 모든 설정값은 `config/` 디렉토리에서 관리 (매직 넘버 금지)

**근거**: 파이프라인 구조에서 한 모듈의 수정이 다른 모듈에 영향을 주면 유지보수 비용이 기하급수적으로 증가한다. 불변성은 데이터 흐름 추적의 핵심이다.

### VII. Evidence-Based Completion (증거 기반 완료)

"완료했습니다"는 증거가 아니다. 실행 결과만이 증거다.

- 모듈 구현 완료 시: 해당 모듈의 단독 실행 결과 MUST 첨부
- 파이프라인 테스트: 최소 3개 블라인드 글로 전체 파이프라인 통과 확인
- 영상 품질 확인: 생성된 MP4 파일의 재생 시간, 해상도, 음성 동기화 육안 확인
- 빌드 검증: TypeScript 타입 체크 통과, ESLint 경고 0개
- 커밋 전: 전체 파이프라인 1회 이상 성공 실행 증거 필수

**근거**: LLM은 실행 없이 "완료"를 선언하는 경향이 있다. 추측성 완료 선언은 디버깅 비용을 10배로 증가시킨다.

## Quality Gates (품질 관문)

### 영상 품질 기준

생성된 모든 쇼츠 MUST 다음 기준을 충족한다:

1. **길이**: 30–60초 (초과/미달 시 재생성)
2. **해상도**: 1080x1920 (9:16) — 720x1280 허용 (개발 단계)
3. **텍스트 가독성**: 화면 중앙 80% 영역, 최소 32px, 고대비
4. **음성 동기화**: TTS 음성과 화면 텍스트 전환 시점 일치 (±1초 이내)
5. **자막 포함**: 전체 음성에 대응하는 자막 표시
6. **감정 일관성**: 배경색/음성톤/텍스트 스타일이 감정 타입과 일치

### 콘텐츠 필터링 기준

1. **개인정보**: 실명, 직급, 부서명, 연락처 → 마스킹 또는 스킵
2. **부적절 표현**: 욕설, 성적 표현, 차별 발언 → 자동 스킵
3. **정치/종교**: 논란성 주제 → 자동 스킵
4. **불법 행위**: 불법 조언, 범죄 관련 → 자동 스킵
5. **광고/스팸**: 홍보성 게시글 → 자동 스킵

## Technical Standards (기술 표준)

| 영역 | 표준 |
|------|------|
| 언어 (백엔드) | Python 3.11+ |
| 언어 (영상) | TypeScript + React (Remotion) |
| AI 분석 | Claude Code (Sonnet 4.6) — 직접 호출 |
| TTS | edge-tts (Microsoft Edge, 무료) |
| 영상 렌더링 | Remotion (로컬 렌더링) |
| 크롤링 | Playwright (Python) |
| 배경 (Phase 1) | Remotion CSS 그라데이션 |
| 배경 (Phase 2) | Pexels API 무료 스톡 영상 |
| 데이터 교환 | JSON 파일 기반 |
| 폰트 | Noto Sans KR (Google Fonts) |
| 패키지 관리 | pip + npm (Python + Node.js 혼합) |
| 형상 관리 | Git + GitHub |

## Development Workflow

| 단계 | 도구 | 설명 |
|------|------|------|
| 원칙 수립 | `/speckit.constitution` | 프로젝트 거버넌스 원칙 정의 |
| 스펙 작성 | `/speckit.specify` | 기능 요구사항 + 수락 시나리오 정의 |
| 명세 명확화 | `/speckit.clarify` | 모호한 요구사항 질의/확인 |
| 구현 계획 | `/speckit.plan` | 기술 설계 + Constitution Check |
| 태스크 분해 | `/speckit.tasks` | 구현 단위 분해 + 의존성 정리 |
| 구현 | `/speckit.implement` | 태스크 단위 구현 (TDD 사이클) |
| 품질 확인 | `/speckit.checklist` | 품질 체크리스트 실행 |
| 코드 분석 | `/speckit.analyze` | 기존 코드 리뷰/분석 |

### 개발 프로세스 흐름

```
/speckit.specify (기능 명세)
    ↓
/speckit.clarify (필요 시 명확화)
    ↓
/speckit.plan (기술 계획 + Constitution Check)
    ↓
/speckit.tasks (태스크 분해)
    ↓
/speckit.implement (구현) × N회 반복
    ↓
/speckit.checklist (품질 확인)
    ↓
커밋 + PR
```

## Governance

- Constitution이 모든 개발 판단의 **최상위 기준**이다. 원칙 간 충돌 시 번호가 낮은 원칙이 우선한다 (I > II > ... > VII).
- 원칙 변경 시: 문서화 + 버전 업 + 영향받는 코드 마이그레이션 계획 필수.
- 모든 새 기능/변경은 Constitution Check를 통과해야 한다.
- 유료 서비스 도입 시 원칙 I 위반 여부를 검토한 후 적용한다.
- 콘텐츠 안전 관련 의사결정은 원칙 IV가 다른 모든 기능 요구보다 우선한다.

**Version**: 1.0.0 | **Ratified**: 2026-03-23 | **Last Amended**: 2026-03-23
