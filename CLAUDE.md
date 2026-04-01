# ContentsMaker Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-26

## Active Technologies

- Python 3.11+ (백엔드), TypeScript 5.9+ (프론트엔드/Remotion)
- Next.js 16, Remotion 4.x, React 19, edge-tts, @dnd-kit/core

## Project Structure

```text
src/               # Python 백엔드 (analyzer, tts, video, editor)
app/               # Next.js 웹 UI + API routes
src/video/remotion/ # Remotion React 프로젝트
data/              # 데이터 (raw, scripts, audio, images, outputs, projects)
```

## Commands

```bash
python3 -m pytest tests/ -v      # Python 테스트
npm run dev                       # Next.js 개발 서버
ruff check .                      # Python 린트
```

## Recent Changes

- 005: 데이터 모델 확장 (SubtitleStyle, TransitionConfig, SfxConfig)
- 005: scene_ops.py (split, merge, reorder, resize) + API endpoints
- 004: Punctuation-based speech pacing (Rule 11)
- 004: Per-scene TTS timing for accurate audio-scene sync

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
