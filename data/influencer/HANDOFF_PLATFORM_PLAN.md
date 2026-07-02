# AI 인플루언서 — 플랫폼 결정 & 실행 계획 (핸드오프)

> 작성 2026-06-12. 별도 신규 프로젝트로 이관용 핸드오프 문서.
> 짝 문서: [`character_concept.md`](./character_concept.md) (페르소나 = Mia Seo / 서미아).
> 이 문서 = **어떤 플랫폼으로, 얼마에, 어떻게** 만들지. character_concept.md = **누구를** 만들지.

---

## 0. TL;DR (결정 요약)

- **플랫폼: Higgsfield 단일** (2026-06-12 사용자 확정). FLUX LoRA(fal/Replicate)·Freepik 자동화 모두 폐기.
- **Freepik Premium+ 구독 종료** (2026-06-12) → 모든 신규 이미지/영상 생성을 Higgsfield로 일원화.
- **요금제: Plus $39/월(연결제, 3,000크레딧/월, 9,000까지 확장)**.
- **캐릭터 고정: Soul ID** (FLUX LoRA 대체). 5분 학습·프롬프트만으로 무제한 생성, 약 95% 일관성.
- **영상: 허브 내 Seedance 2.0(히어로)·Kling 3.0(b-roll).**
- **통합: Higgsfield Cloud API(cloud.higgsfield.ai) + CLI/MCP(`npm i -g @higgsfield/cli`).**

---

## 1. 플랫폼 조사 결과 (의사결정 근거)

### 1-1. 후보군 비교 — 영상 AI

| 플랫폼 | 유형 | 인물 일관성 | 시작가 | 비고 |
|---|---|---|---|---|
| **Higgsfield** ✅채택 | 구독형 스튜디오 + Cloud API | **Soul ID(100+ 파라미터)** | $15~ / Plus $39 | AI 인플루언서·UGC 공장 표준. Sora2/Veo3.1/Kling3.0/Wan2.6/Seedance2.0/Hailuo 통합 |
| fal.ai | API 허브 | FLUX LoRA 직접 | 종량 | DX 좋음, 영상 단가 비쌈(Seedance $0.30/s) |
| Replicate | API 허브 | FLUX LoRA 직접 | 종량 | LoRA 학습 ~$1.85/회, 투명 종량제 |
| WaveSpeedAI | API 허브 | FLUX/Wan LoRA 학습 | 종량 | 이미지 $0.015/장, Seedance 20%↓, 가성비 |
| Runway | 자사모델 단일 | Gen-4 References | $12~ | 인물 likeness 강하나 복잡 장면 약함, 단가 높음 |
| Krea | 멀티모델 캔버스 | 참조 기반 | $9 | 이미지 반복 작업, 단가 비쌈 |
| Pika / Luma | 구독형 | 중 | $10 / $9.99 | 가성비 영상, 인물 전용 기능 약함 |
| GamsGo (Rita AI) | 공유구독 번들 | 모델 의존 | $11.99 | 30+ 모델 묶음. **공유계정 ToS 리스크·API 불가** → 제외 |

### 1-2. 영상 모델 단가 참고 (API 기준, USD/초)

| 모델 | 단가 | 메모 |
|---|---|---|
| Seedance 2.0 Fast | $0.022/s | 프로덕션급 최저가, 리더보드 1위 |
| Vidu 2.0 | $0.0375/s | 저가 |
| Hailuo 2.3 | ~$0.047/s | 인물 모션 |
| Kling 3.0 base | $0.029/s | 표정·동작 안정 |
| Veo 3.1 | $0.03/s | 네이티브 오디오 포함 |
| PixVerse v5.5 | $0.03~0.08/s | 해상도별 |
| Wan 2.2 | $0.1/s | — |

> Higgsfield는 위 모델들을 **구독 크레딧 안에서** 사용 → 변동비를 고정 구독으로 흡수.

### 1-3. 이미지 + FLUX LoRA 참고 (Higgsfield 밖 옵션)

| 항목 | 단가 |
|---|---|
| FLUX LoRA 학습 | Replicate ~$1.85/회, fal/WaveSpeed ~$2 |
| FLUX LoRA 이미지 | WaveSpeed $0.015, Runware $0.0006~$0.0038, fal $0.021 |

---

## 2. 핵심 기술 판단: Soul ID vs FLUX LoRA

**Higgsfield는 FLUX LoRA 학습/업로드를 지원하지 않는다.** 대신 자체 **Soul ID**로 동일 목표(인물 1명 고정)를 달성한다.

| | Soul ID (Higgsfield) | FLUX LoRA (fal/Replicate/Civitai) |
|---|---|---|
| 학습 | 사진 20+장 → 5분, 40크레딧(~$2.5) | 데이터셋·스텝 튜닝, ~$2/회 |
| 사용 | 프롬프트만으로 무제한, 참조 재업로드 불필요 | LoRA 로드 + 참조 병행 |
| 일관성 | ~95% (프롬프트 단독) | LoRA+참조 시 95%+ |
| 결과물 소유 | ❌ 내부 종속 (파일 추출 불가) | ✅ .safetensors 이식 가능 |

**결론:** 인플루언서 양산엔 Soul ID로 충분·더 적합(운영 단순). **FLUX LoRA가 필요한 경우는** ① LoRA 파일 소유/ComfyUI 이식 ② Higgsfield 종속 회피 ③ 특정 컷 정밀 제어 — 이때만 Higgsfield 밖에서 별도 학습(이원 운영).

---

## 3. Higgsfield 요금·크레딧 사실관계

- **요금제(연결제):** Starter $15(70크레딧) / Plus $39(3,000, 9,000까지) / Ultra $99(9,000). Free 10크레딧/일.
- **환산:** $1 = 16크레딧. 탑업 $5/100크레딧.
- **소진 단가:** Soul ID 생성 40크레딧(~$2.5, 1회) · 이미지 1.5~3크레딧(~$0.09~0.19/장) · Kling 3.0 영상 ~6크레딧.
- **주의:** 구독 크레딧 **이월 불가·월말 소멸**. 탑업 크레딧 **90일 만료**(미리 대량 구매 금지).
- **개발 접근:** Cloud API(cloud.higgsfield.ai) + CLI/MCP(`npm i -g @higgsfield/cli`, `higgsfield auth login`). WaveSpeed 경유 Soul image-to-image API도 존재.
- **알려진 한계:** Soul ID가 Kling Motion Control과 미통합 → 멀티샷 시 얼굴 드리프트 가능 → 핵심 컷은 참조 고정 필요.
- **크레딧 감각(Plus 3,000/월):** 이미지 ~1,000장 또는 Kling 영상 ~500편 또는 혼합.

---

## 4. 실행 계획 (Phase)

**Phase 0 — 셋업 (1일)**
- Higgsfield **Plus** 연결제 구독.
- CLI/MCP 인증(`higgsfield auth login`) → 신규 프로젝트에서 직접 호출 연결.
- (Starter 70크레딧은 Soul ID 1개+α면 소진 → 양산 부적합, Plus가 실질 최소선.)

**Phase 1 — 캐릭터 락인 (1일)**
- `character_concept.md` §2·§5 외모 스펙으로 후보 시안 3~5종 생성 → 1종 선택.
- 동일 인물 15~20장(다각도×두 헤어 상태×운동복/오피스룩×조명) → **Soul ID 학습(40크레딧)**.
- 검증: 운동/오피스 각 5장 생성, 얼굴·체형·앵커(골드 뱅글·주근깨) 일관성 육안 평가.

**Phase 2 — 이미지 양산 (반복)**
- Soul 2.0로 포즈·의상·배경 변주. 콘텐츠 믹스 힙업40/서울라이프40/서사20.
- IG 주력 캐러셀 + 이중언어 캡션.

**Phase 3 — 영상 클립 (반복)**
- Soul 이미지 → i2v: **Seedance 2.0**(스쿼트 등 동작·해부학) / **Kling 3.0**(표정·b-roll). 9:16.
- 실측 비교(스쿼트 1 + 카페 b-roll 1)로 모델 우선순위 확정.

**Phase 4 — 합성·업로드**
- 클립 다운로드 → 편집·자막 합성 → IG/Shorts/TikTok.
- 게시 전 **수동 검수 필수**(SFW 가드, §8). AI 라벨 필수.
- 영상 1편마다 **3줄 요약 + 해시태그** 동반(고정 규칙).

---

## 5. 비용 모델

- **고정비:** Higgsfield Plus $39/월.
- **변동비:** 구독 크레딧 내 흡수. 초과 시 탑업 $5/100크레딧.
- **Soul ID 학습:** ~$2.5/회(1회성, 재학습 시만).
- 월 산출 목표(피드 주 5~7 + 스토리 매일)는 Plus 3,000크레딧 내에서 운용 가능, 부족 시 9,000까지 확장 또는 Ultra.

---

## 6. 미결 / 인계 시 결정할 것

1. **정치/토픽 쇼츠 파이프라인** — 기존 ContentsMaker의 video 모드(Freepik으로 Kling/Wan $0 생성)는 Freepik 구독 종료로 **동작 불가**. (a) Higgsfield 통합 (b) 원본 뉴스클립 위주라 AI 영상 불필요 → 해당 모드 비활성, 중 택1 필요. ※ 이건 인플루언서와 별개 라인.
2. **Soul ID 단독 vs FLUX LoRA 이원** — 기본은 Soul ID 단독. LoRA 파일 소유/ComfyUI 정밀 제어 필요해지면 그때 보조 추가.
3. **이름 확정** — Mia Seo / Hana Reed / Erin Kang 중 택1 (character_concept.md §1).

---

## 7. 참고 링크

**Higgsfield**
- 공식 요금제: https://higgsfield.ai/pricing
- Cloud API: https://cloud.higgsfield.ai/
- Soul ID 소개: https://higgsfield.ai/blog/SOUL-ID-Superior-Level-of-AI-Character-Consistency
- Soul ID 테스트(일관성 실측): https://medium.com/@302.AI/higgsfield-soul-id-test-how-realistic-is-the-character-consistency-1bc8b3250bca
- MCP 가이드: https://www.solosoft.dev/post/higgsfield-ai-mcp-guide-2026/

**비교/단가 참고**
- Cheapest AI Video APIs 2026 (Atlas Cloud): https://www.atlascloud.ai/blog/guides/cheapest-ai-video-generation-api-2026
- 17 Best AI Video Models Pricing & API: https://aifreeforever.com/blog/best-ai-video-generation-models-pricing-benchmarks-api-access
- Higgsfield vs Krea: https://oakgen.ai/vs/higgsfield-vs-krea
- AI 인플루언서 수익화(Higgsfield, Scribe): https://scribehow.com/page/How_to_Make_Money_with_AI_Influencers_Using_Higgsfield_in_2026__lXAEk5qtSkG0vXZyiA-bDA

**FLUX LoRA (밖 옵션)**
- fal FLUX LoRA Fast Training: https://fal.ai/models/fal-ai/flux-lora-fast-training
- Replicate fast-flux-trainer: https://replicate.com/replicate/fast-flux-trainer/train
- WaveSpeed Flux LoRA Trainer: https://wavespeed.ai/docs/docs-api/wavespeed-ai/flux-dev-lora-trainer
