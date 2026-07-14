"""compute_aligned_bounds 순수 함수 테스트 — 무음 트림 + 앵커 스냅 + 단조성."""
from src.tts.silence_align import compute_aligned_bounds


def test_trailing_silence_is_trimmed_from_speech_span():
    # 20초 오디오인데 12~20초가 무음 → 발화 구간은 0~12초여야 함.
    ss, se, bounds = compute_aligned_bounds(
        duration=20.0,
        silences=[(12.0, 20.0)],
        scene_durations_ms=[1000, 1000],
    )
    assert ss == 0.0
    assert abs(se - 12.0) < 1e-6
    assert abs(bounds[-1] - 12.0) < 1e-6  # 마지막 경계 = 발화 끝


def test_leading_and_trailing_silence_trimmed():
    ss, se, bounds = compute_aligned_bounds(
        duration=20.0,
        silences=[(0.0, 1.0), (12.0, 20.0)],
        scene_durations_ms=[1000, 1000],
    )
    assert abs(ss - 1.0) < 1e-6
    assert abs(se - 12.0) < 1e-6
    assert abs((se - ss) - 11.0) < 1e-6


def test_internal_boundary_snaps_to_confident_silence():
    # 두 씬, 글자수 동일이면 추정 경계는 6초. 5초에 무음이 있으면 거기에 스냅.
    ss, se, bounds = compute_aligned_bounds(
        duration=12.0,
        silences=[(4.8, 5.2), (12.0, 12.0)],
        scene_durations_ms=[1000, 1000],
    )
    assert abs(bounds[1] - 5.0) < 1e-6  # 무음 중심 5.0에 스냅


def test_bounds_are_monotonic_and_cover_full_span():
    ss, se, bounds = compute_aligned_bounds(
        duration=19.42,
        silences=[(2.09, 2.61), (4.98, 5.98), (9.78, 10.84), (15.22, 16.31), (19.42, 19.42)],
        scene_durations_ms=[28, 33, 42, 27, 50, 48, 17, 24],
    )
    assert bounds[0] == 0.0
    assert all(bounds[i] < bounds[i + 1] for i in range(len(bounds) - 1))
    assert len(bounds) == 9  # 8 scenes → 9 bounds


def test_no_silence_falls_back_to_proportional():
    ss, se, bounds = compute_aligned_bounds(
        duration=10.0,
        silences=[],
        scene_durations_ms=[1000, 3000],  # 1:3 비율
    )
    assert abs(se - 10.0) < 1e-6
    assert abs(bounds[1] - 2.5) < 1e-6  # 10초 * 1/4
