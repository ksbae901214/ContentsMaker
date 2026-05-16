# Test fixtures (T121)

Large binary fixtures for smoke tests are NOT committed (see `.gitignore`).

## Required for `test-e2e --real-models`

| File | Purpose | Source |
|---|---|---|
| `natv_sample.mp4` | 10분 분량 NATV 국회방송 발언 1건 | NATV YouTube 채널에서 yt-dlp 로 1편 다운로드 후 ffmpeg trim |

### 준비 방법

```bash
# 1. NATV 채널에서 짧은 본회의/위원회 1건 ID 확인
python3 -m src.dem_shorts.cli poll-natv --since-hours 24 --dry-run | head

# 2. 영상 다운로드
python3 -m src.dem_shorts.cli download --video-id <VIDEO_ID>

# 3. 10분으로 트리밍
ffmpeg -i data/dem_shorts/archive/<VIDEO_ID>.mp4 -t 600 -c copy tests/fixtures/natv_sample.mp4

# 4. 실제 모델 스모크 실행 (5~10분)
python3 -m src.dem_shorts.cli test-e2e --real-models
```

또는 환경변수로 다른 위치 지정:

```bash
export NATV_SMOKE_SAMPLE=/path/to/your.mp4
python3 -m pytest tests/dem_shorts/test_e2e_smoke.py::test_smoke_real_pipeline_with_local_sample
```

`tests/fixtures/natv_sample.mp4` 가 없으면 `test_smoke_real_pipeline_with_local_sample` 는 자동 skip 처리되며 stub 모드 테스트만 실행된다.
