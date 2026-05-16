# CLI Contract: Phase 6 확장 커맨드

## 기존 커맨드 확장

### `python3 -m src.main pipeline`

```bash
python3 -m src.main pipeline \
  --file data/raw/input.json \
  --visual-mode manga \        # 신규: "manga" (기본) | "video"
  --image-style webtoon \      # 신규: "webtoon" (기본) | "3d_pixar" | "realistic" | "anime"
  --no-images                  # 기존: 이미지 생성 스킵
```

### `python3 -m src.main render`

```bash
python3 -m src.main render \
  --script data/scripts/xxx.json \
  --audio data/audio/xxx.mp3 \
  --scene-videos data/videos/  # 신규: 영상 클립 디렉토리
```

## 신규 커맨드

### `python3 -m src.main topic`

```bash
python3 -m src.main topic \
  --topic "즐겨 먹던 과자들의 배신" \
  --style narration \          # "narration" | "skit" | "review"
  --tone "재밌게" \
  --details "추가 설명" \
  --visual-mode manga \
  --image-style 3d_pixar
```

**동작**: topic → save_topic() → analyze_topic() → 이미지/영상 생성 → TTS → render

## 파이프라인 분기 로직

```
mode 판별:
  topic → TopicInput → analyze_topic(visual_mode)
  기타  → BlindPost → analyze(visual_mode)

visual_mode 판별:
  manga → build_image_prompts(script, image_style) → generate_scene_images()
  video → SeedanceGenerator.generate_and_wait() per scene

이후 공통:
  → generate_voice_with_timing()
  → render_video(scene_images=..., scene_videos=...)
```
