# Politics Bias Charter — ContentsMaker Party-Shorts

**Version**: 1.0.0
**Ratified**: 2026-04-20
**Owner**: ContentsMaker project operator
**Scope**: `src/dem_shorts/` 모듈(후속 `party_shorts`로 리네임 예정) 및 연관 `specs/007-dem-shorts-studio/`, `app/dem-shorts/`, `app/api/dem-shorts/`

---

## 1. Preamble

본 시스템(NATV 기반 정치 쇼츠 반자동 제작)은 **특정 정당 편향을 강제하지 않는다**. 편향의 방향은 전적으로 운영자가 선택한 `party_perspective`에 의해 결정되며, 시스템은 선택된 관점에 대해 대칭적인 가드레일·게이트·리포트를 제공한다.

이 문서는 본 시스템을 운영하며 지켜야 할 정치적 공정성·법적 준수·윤리 원칙을 명문화한다. ContentsMaker Constitution(`.specify/memory/constitution.md`)의 원칙 IV(Content Safety & Legal Compliance)를 perspective 축 도입 맥락에서 확장한다.

---

## 2. Supported Perspectives

현재 시스템이 지원하는 `party_perspective`는 다음 2가지로 한정한다.

| id | label | 친화 대상 | 현재 상태 |
|----|-------|-----------|-----------|
| `dem` | 민주당 관점 | 더불어민주당·조국혁신당 중심 | channel_id=NULL, 로컬 렌더 전용 (업로드 비활성) |
| `ppp` | 국민의힘 관점 | 국민의힘·개혁신당(alliance) 중심 | channel_id=`@국회직캠-d6r`, **프로덕션 채널** |

무소속·제3당 전용 perspective는 본 charter 범위 밖이며, 추후 신규 feature로 분리해 추가한다.

---

## 3. Founding Principles

### 3.1 운영자 책임 원칙
시스템은 도구일 뿐이며, **최종 콘텐츠의 합법성·윤리성 책임은 전적으로 운영자(프로젝트 오너)에게 있다**. 시스템의 자동 가드레일 통과는 책임 면제의 근거가 되지 않는다.

### 3.2 대칭 원칙 (Symmetry)
시스템의 편향 감지·가드레일·리포트는 활성 perspective를 기준으로 **양방향 대칭**으로 작동해야 한다.
- "우리편 과도 옹호"와 "반대편 과도 비방"은 동일하게 경고·차단 대상이다.
- 이를 구체화한 메커니즘이 **Symmetry Gate(FR-025 item 11)**: 해설 스크립트를 현재 perspective와 반대 perspective 각각으로 평가했을 때 risk_score 차이가 20점을 초과하면 경고(첫 30일) 또는 차단(31일 이후).
- Symmetry Gate의 운영자 override는 허용하되 감사 로그가 반드시 남는다(SC-013 연관).

### 3.3 채널-관점 1:1 고정 원칙 (Channel-Perspective Binding)
하나의 YouTube 채널은 **정확히 하나의 perspective**와 매핑된다.
- `perspectives.channel_id`는 UNIQUE 제약으로 강제된다.
- 업로드 시 `uploader.py`가 perspective ↔ channel_id 불일치를 감지하면 TypeError로 즉시 차단(SC-014).
- 한 채널 내에서 두 perspective를 혼합 운영하는 것은 **Out of Scope**이며 시스템이 기술적으로 차단한다.

### 3.4 선거법 공정성 원칙 (Election Law Neutrality)
선거기간 가드(FR-030~FR-032)는 perspective와 **무관하게** 작동한다.
- 대선 D-180 / 총선 D-120 경계 이후 모든 perspective의 commentary 톤은 "정책 설명 중심"으로 자동 전환.
- 특정 후보·정당 우호 표현 금지 룰은 양 perspective에 동일 적용.
- 중립 모드에서의 risk_score 임계값은 30점으로 동일 하향.

### 3.5 가드레일 대칭 사전 원칙
- **공통 사전** (정당 무관): `hate` / `defamation` / `bias` / `false_claim` 4개 카테고리의 기본 키워드는 좌·우 양측 멸칭·과장 표현을 혼재 수록 (현행 유지, `keyword_dict.py`).
- **perspective별 서브사전**: 각 perspective는 `against_us`(우리편을 공격하는 관용어 탐지) / `about_them`(우리가 반대편을 부당 낙인할 때 차단) 2종을 대칭적으로 보유한다.
- 어느 한쪽만 강화되면 대칭 원칙 위반이며 본 charter 위반으로 간주한다.

### 3.6 명예훼손 임계값 대칭 원칙
- `RISK_SCORE_BLOCK`(현재 61.0), `RISK_SCORE_BLOCK_ELECTION`(현재 30.0)은 perspective 무관 동일 적용.
- 특정 perspective만 관대하거나 엄격한 임계값을 두지 않는다.

---

## 4. Legal Consultation Policy

### 4.1 자문 대상 범위
본 시스템 운영 전 및 perspective 축 확장 시마다 정치·언론 전문 변호사 1회 이상 자문을 받는다. 자문 범위:
- 공직선거법 (선거기간 가드·중립 모드)
- 정보통신망법 (명예훼손 임계값)
- 정치자금법 (채널 수익화 방식)
- YouTube 커뮤니티 가이드 (정치 콘텐츠 정책)
- **양 perspective 공존 아키텍처의 "허위 영향 미치기" 해석 가능성**

### 4.2 현재 상태 (2026-04-20)
- 007 최초 구현 시점(2026-04-16)에 "민주당 친화형" 전제 자문 완료 기록 있음.
- perspective 축 추가에 따른 **재자문 pending**.
- **본 charter 기반 Phase 0 완료 후 변호사 재자문이 완료되기 전까지 프로덕션 업로드 금지**. 로컬 렌더·dry-run upload는 개발 목적으로 허용.

### 4.3 PPP 시드 인물 선정 적법성
본 charter 작성 시점 PPP perspective의 pinned 시드 6명(한동훈·김기현·권성동·추경호·나경원·오세훈)은 모두 **공개된 공인(공직자·전직 공직자·당대표급 정치인)**으로, 선정 자체는 공적 관심 영역 내이다. 다만 시드 등록 사실 자체를 "사찰 명단"으로 오인시키는 외부 표현(예: 채널 설명·메타데이터)을 해서는 안 된다.

---

## 5. Operational Policies (본 채널 적용)

### 5.1 단일 perspective 운영
- 현재 프로덕션 채널(`@국회직캠-d6r`)은 **`ppp` perspective only** 운영.
- `dem` perspective는 로컬 렌더 테스트·회귀 검증 용도로만 사용.
- 5:5 균형 업로드는 강제하지 않는다(사용자 Q6 결정).

### 5.2 내부 다양성 모니터링
단일 perspective 내에서도 특정 인물 편중 방지:
- 월간 편향 리포트(FR-038)에서 활성 perspective 내 특정 인물 비중이 30%를 초과하면 경고.
- PPP 관점의 경우 한동훈/김기현/권성동/추경호/나경원/오세훈 6인 중 임의 3인 합계 60% 이하 유지 목표(SC-011).

### 5.3 콘텐츠 방향성
현재 채널 주력 콘텐츠(한국은행 총재 인사청문회 비판 등)는 **여당 지명 인사에 대한 야당 관점 검증**이며, 이는 헌법이 보장하는 건전한 정치 비판 영역 내에 있다. 단, 다음은 항상 준수한다:
- 단정적 명예훼손 표현 금지 (가드레일 자동 감지)
- 팩트 출처 최소 2개 첨부 (FR-029)
- 원본 비율 50% 이하, 본인 해설 50자 이상 (FR-025 item 1·2)
- NATV 출처 명시 (FR-025 item 4)

---

## 6. Audit & Evidence Trail

### 6.1 보존 대상
- 원본 NATV 영상 파일: 최소 1년 (FR-040)
- 편집 이력·가드레일 통과 기록·Symmetry override 서명: 최소 2년 (명예훼손 피소 대응 증거)
- perspective별 배치 로그(랭킹·리포트·가드레일 재학습): 최소 1년

### 6.2 운영자 서명 (Signed Override)
FR-025 item 9·10·11에 대해 운영자 수동 서명이 발생하면 다음을 기록:
- timestamp (UTC)
- operator_id (운영자 식별자)
- draft_id
- item_id
- override_reason (자유 입력, 최소 30자)
- 해설 스크립트 당시 스냅샷 (immutable)

### 6.3 Periodic Review
- **매월 1일** (자동): perspective별 편향 리포트 생성·검토.
- **매분기 1일** (수동): 본 charter의 §2 perspective 정의·§3 원칙 재평가.
- **매년 변호사 자문 갱신** 권장.

---

## 7. Charter Amendment

본 charter의 개정은 다음 절차를 따른다.
1. 개정 내용 문서화 + 버전 업 (SemVer).
2. `CHANGELOG`에 변경 사유·영향 범위 기록.
3. ContentsMaker Constitution의 원칙 IV와 정합성 확인.
4. 필요 시 변호사 자문.
5. 코드·스펙(`specs/007-dem-shorts-studio/spec.md`)과 charter가 상충할 경우 charter 우선.

---

## 8. Revision History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0.0 | 2026-04-20 | 최초 작성 — perspective 축(dem/ppp) 도입, Symmetry Gate 원칙, 채널 1:1 바인딩, PPP-only 운영 정책 명문화 | operator + claude-code |

---

**문서 서명 대기**: 본 charter는 초안 상태이며, 운영자 및 법률 자문의 서명을 받은 후 활성화된다.
