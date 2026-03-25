# 다음 세션 핸드오프

## 즉시 구현할 기능: 씬별 편집 (이미지 교체 + 대본 수정 + 프롬프트 편집)

### 작업 명령어
```
/auto 씬별 편집 기능 구현: 결과 화면에 씬 카드(이미지+대본+프롬프트), 이미지 교체 모달(프롬프트 편집+재생성/수정재생성/업로드 3버튼), 대본 인라인 편집, 영상 재렌더링
```

### 구현 상세

#### 1. route.ts 결과 데이터 확장
결과에 추가 전달:
```json
{
  "scriptPath": "data/scripts/xxx.json",
  "audioPath": "data/audio/xxx.mp3",
  "sceneImages": [
    {"sceneId": 1, "imagePath": "data/images/xxx_scene_01.png", "prompt": "CRITICAL — ..."}
  ]
}
```

#### 2. 결과 화면 씬 카드 (page.tsx)
- 영상 프리뷰 아래에 씬별 카드 그리드
- 각 카드: 이미지 썸네일 + 대본 텍스트
- 이미지 클릭 → 교체 모달
- 대본 클릭 → textarea 인라인 편집
- 수정된 항목에 배지 표시

#### 3. 이미지 교체 모달
- 현재 이미지 미리보기
- 프롬프트 textarea (원본 표시, 편집 가능)
- 3 버튼: 재생성(같은프롬프트) / 수정후재생성 / 업로드
- $0.005 비용 안내

#### 4. API 엔드포인트 3개
| API | 용도 |
|-----|------|
| POST /api/regenerate-image | 프롬프트(원본/수정)로 특정 씬 이미지 재생성 |
| POST /api/replace-image | 사용자 업로드 이미지로 교체 |
| POST /api/re-render | 수정된 이미지+대본으로 영상 재렌더링 |

#### 5. 재렌더링 로직
- 이미지만 변경 → render_video() 재호출
- 대본 변경 → TTS 재생성 + render_video() 재호출
- 기존 script.json 수정 후 저장

### 현재 브랜치
`004-bgm-subtitle-url`

### 주의사항
- image_generator.py의 generate_scene_images()를 단일 씬용으로 호출 가능하게 수정 필요
- 프롬프트는 prompt_builder.py에서 생성된 전체 프롬프트 (REFERENCE_STYLE_PREFIX 포함)
- page.tsx는 display:none 탭 방식 사용 중 (hydration 에러 방지)
