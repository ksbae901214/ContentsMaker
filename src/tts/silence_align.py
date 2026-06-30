"""실측 무음 기반 자막-음성 정렬 (Whisper 불필요, ffmpeg만 사용).

Gemini TTS는 전체 텍스트를 한 번에 합성하므로 (1) 발화 뒤에 긴 무음이 붙고
(2) 씬별 타이밍이 글자수 비례 추정이라 발화 속도·쉼·숫자 발음에 따라 자막이 밀린다.

이 모듈은 합성된 오디오에서 실제 무음 구간을 검출해:
  1. 앞뒤 무음을 잘라낸 발화 전용 오디오를 만들고,
  2. 씬 경계를 내부 무음 구간에 스냅(실측)하여 자막이 발화에 맞도록 타이밍을 재계산한다.
무음 경계가 없는 인접 씬은 글자수 비례 추정값을 발화 구간 길이에 맞춰 사용한다.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_SIL_RE = re.compile(r"silence_(start|end):\s*(-?[\d.]+)")


def detect_silences(audio_path: Path, *, noise_db: float = -30.0, min_dur: float = 0.18) -> list[tuple[float, float]]:
    """ffmpeg silencedetect → [(start, end), ...] 초 단위."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(audio_path),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts: list[float] = []
    ends: list[float] = []
    for m in _SIL_RE.finditer(proc.stderr):
        (starts if m.group(1) == "start" else ends).append(float(m.group(2)))
    return list(zip(starts, ends))


def probe_duration(audio_path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def compute_aligned_bounds(
    *,
    duration: float,
    silences: list[tuple[float, float]],
    scene_durations_ms: list[int],
    snap_window: float = 1.5,
    edge_eps: float = 0.06,
    min_scene: float = 0.25,
) -> tuple[float, float, list[float]]:
    """발화 구간 [speech_start, speech_end] + 씬 경계 시간(발화 구간 기준 상대 초)을 계산.

    Returns: (speech_start, speech_end, bounds) — bounds 길이 = 씬 수 + 1, bounds[0]=0.
    순수 함수 (ffmpeg 호출 없음) — 단위 테스트 대상.
    """
    speech_start = 0.0
    speech_end = duration
    if silences and silences[0][0] <= edge_eps:
        speech_start = silences[0][1]
    if silences and silences[-1][1] >= duration - edge_eps:
        speech_end = silences[-1][0]
    span = max(speech_end - speech_start, 0.01)

    # 내부 무음 중심점 (발화 구간 기준 상대 초)
    centers = sorted(
        (s + e) / 2 - speech_start
        for (s, e) in silences
        if s > speech_start + edge_eps and e < speech_end - edge_eps
    )

    total = sum(scene_durations_ms) or 1
    n = len(scene_durations_ms)            # 씬 수 → 내부 경계 m = n-1
    m = n - 1
    # 글자수 비례 누적 경계 추정 (발화 구간 길이로 스케일) — 앵커 보간·폴백 용도
    est = [0.0]
    acc = 0
    for d in scene_durations_ms[:-1]:
        acc += d
        est.append(acc / total * span)
    est.append(span)
    internal_est = est[1:-1]               # 내부 경계 추정 m개

    # 무음(centers)을 내부 경계에 '순서 보존 + 양방향 스킵 허용 + 매칭 창' DP로 배정.
    # 무음·경계 수가 달라도(s>m 또는 s<m) 동작하며, 창(snap_window) 밖이면 매칭 안 함.
    s = len(centers)
    anchor: dict[int, float] = {}          # 내부경계 idx(0..m-1) -> 앵커 시간
    if s and m:
        INF = float("inf")

        def reward(i: int, j: int) -> float:
            # 창 안이면 가까울수록 큰 보상(>0), 밖이면 매칭 불가.
            d = abs(internal_est[i] - centers[j])
            return (snap_window - d) if d <= snap_window else -INF

        # dp[i][j] = 경계 0..i-1, 무음 0..j-1 사용 시 최대 매칭 보상
        dp = [[0.0] * (s + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, s + 1):
                best = dp[i - 1][j]                 # 경계 i-1 미매칭
                if dp[i][j - 1] > best:
                    best = dp[i][j - 1]             # 무음 j-1 미사용
                r = reward(i - 1, j - 1)
                if r > -INF and dp[i - 1][j - 1] + r > best:
                    best = dp[i - 1][j - 1] + r     # 매칭 (보상)
                dp[i][j] = best
        # 역추적
        i, j = m, s
        while i > 0 and j > 0:
            r = reward(i - 1, j - 1)
            if r > -INF and abs(dp[i][j] - (dp[i - 1][j - 1] + r)) < 1e-9:
                anchor[i - 1] = centers[j - 1]
                i -= 1
                j -= 1
            elif abs(dp[i][j] - dp[i - 1][j]) < 1e-9:
                i -= 1
            else:
                j -= 1

    # 앵커 사이 비앵커 경계는 글자수 비례로 보간 (단조 보장).
    # known: (경계 위치 0..n, 시간). 0→0.0, n→span, 앵커들.
    known = {0: 0.0, m + 1: span}
    for idx, t in anchor.items():
        known[idx + 1] = t                 # internal idx → 경계 위치 idx+1
    pts = sorted(known)
    bounds = [0.0] * (m + 2)
    bounds[0], bounds[m + 1] = 0.0, span
    for a, b in zip(pts, pts[1:]):
        ta, tb = known[a], known[b]
        seg_w = scene_durations_ms[a:b] or [1]
        tot_w = sum(seg_w) or 1
        cur = ta
        for k, w in enumerate(seg_w[:-1]):
            cur += (w / tot_w) * (tb - ta)
            bounds[a + 1 + k] = cur
        bounds[b] = tb

    # 단조 증가 + 최소 씬 길이 보장
    for i in range(1, len(bounds)):
        if bounds[i] <= bounds[i - 1] + min_scene:
            bounds[i] = bounds[i - 1] + min_scene
    bounds[-1] = max(span, bounds[-2] + min_scene)
    return speech_start, speech_end, bounds


def align_timings_to_silence(
    audio_path: Path,
    timings: list[dict],
    *,
    out_dir: Path | None = None,
    noise_db: float = -30.0,
    min_dur: float = 0.35,
) -> tuple[Path, list[dict]]:
    """오디오 앞뒤 무음 트림 + 씬 경계 무음 스냅 → (트림된 오디오 경로, 새 timings).

    timings: [{"scene_id", "start_ms", "end_ms"}, ...] (scene_id=-1 outro는 제외 처리).
    """
    out_dir = out_dir or audio_path.parent
    main = [t for t in timings if t.get("scene_id") != -1]
    if not main:
        return audio_path, timings

    duration = probe_duration(audio_path)
    silences = detect_silences(audio_path, noise_db=noise_db, min_dur=min_dur)
    scene_durs = [int(t["end_ms"] - t["start_ms"]) for t in main]

    speech_start, speech_end, bounds = compute_aligned_bounds(
        duration=duration, silences=silences, scene_durations_ms=scene_durs,
    )

    # 발화 구간만 트림 (앞뒤 무음 제거)
    trimmed = out_dir / f"{audio_path.stem}_aligned.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{speech_start:.3f}", "-to", f"{speech_end:.3f}",
         "-i", str(audio_path), "-c:a", "libmp3lame", "-q:a", "2", str(trimmed)],
        check=True,
    )

    new_timings = [
        {"scene_id": t["scene_id"],
         "start_ms": int(bounds[i] * 1000),
         "end_ms": int(bounds[i + 1] * 1000)}
        for i, t in enumerate(main)
    ]
    return trimmed, new_timings
