# Remotion V3 — 정치쇼츠 V3 격리 패키지

기존 `src/video/remotion/` (V1/V2)와 **완전 격리**된 독립 Remotion 패키지.

## 초기 설정

```bash
cd src/video/remotion_v3
npm install
```

별도 `node_modules/`가 생성되며, V1/V2 영상 생성에는 영향 없음.

## 명령

| 명령 | 설명 |
|---|---|
| `npm run preview` | 브라우저에서 4종 레이아웃 미리보기 |
| `npm run build` | `JpoliticsShorts` composition을 `out/video.mp4`로 렌더 |
| `npm run typecheck` | `tsc --noEmit` 타입 체크 |

## Lock-in 사항 (사용자 명시, 2026-06-05)

- **워터마크 없음** — 채널 로고 표시 안 함
- **효과음(SFX) 0** — `<Audio>` 트랙은 TTS 1개만
- **씬 전환 효과 0** — 그라데이션·페이드·디졸브 미사용, 하드 컷
- **TTS 씬 간 gap 300 ms** — Python TTS 단계에서 처리, Remotion은 결과 audio.mp3만 사용

## 레이아웃 4종

- `normal` → `<TalkingHeadScene />`
- `vs_card` → `<VsCardScene />`
- `grid_2x2` → `<ComparisonGridScene />`
- `data_card` → `<DataCardScene />`
