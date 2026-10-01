"""정치쇼츠 BGM 은 어두운 트랙만 (사용자 지시 2026-09-18).

실측 근거 — 고역(4kHz+) mean_volume, 40초 구간:
    relatable_1 -36.9 / angry_3 -39.0 / angry_2 -43.2 / relatable_3 -43.2
    touching_1  -44.6 / relatable_2 -45.2 / touching_3 -56.7 / touching_2 -65.7
`touching` 으로 지정해도 에너지 점수가 낮으면 인덱스 0(`touching_1`, -44.6dB)이
뽑혀 relatable_2 와 밝기가 거의 같다. 그래서 emotion 이 아니라 **풀 자체**를
어두운 두 트랙으로 좁힌다.
"""
from src.analyzer.script_models import (
    AudioConfig, BackgroundConfig, Metadata, Scene, ShortsScript,
)
from src.tts.voice_config import DARK_BGM_FILES, select_bgm_for_script


def _script(*, source_type: str, emotion: str, n_scenes: int,
            emphasis: bool, duration: float) -> ShortsScript:
    scenes = tuple(
        Scene(id=i, timestamp=float(i), duration=duration / max(n_scenes, 1),
              type="body", text=f"씬 {i}", voice_text=f"씬 {i}",
              subtitle_emphasis=emphasis)
        for i in range(n_scenes)
    )
    return ShortsScript(
        metadata=Metadata(title="t", emotion_type=emotion, duration=duration,
                          source_type=source_type),
        scenes=scenes,
        audio=AudioConfig(tts_script="x"),
        background=BackgroundConfig(),
    )


class TestPoliticalDarkBgm:
    def test_political_low_energy_still_dark(self):
        """에너지 점수가 최저여도 밝은 touching_1 이 나오면 안 된다."""
        s = _script(source_type="political_pro", emotion="touching",
                    n_scenes=3, emphasis=False, duration=20.0)
        assert select_bgm_for_script(s) in DARK_BGM_FILES

    def test_political_high_energy_still_dark(self):
        s = _script(source_type="political_pro", emotion="touching",
                    n_scenes=8, emphasis=True, duration=60.0)
        assert select_bgm_for_script(s) in DARK_BGM_FILES

    def test_political_ignores_bright_emotion(self):
        """config 가 relatable/angry/funny 여도 정치면 어두운 트랙으로 고정."""
        for emotion in ("relatable", "angry", "funny"):
            s = _script(source_type="political_pro", emotion=emotion,
                        n_scenes=6, emphasis=True, duration=42.0)
            assert select_bgm_for_script(s) in DARK_BGM_FILES, emotion

    def test_dark_pool_excludes_touching_1(self):
        """touching_1 은 -44.6dB 로 relatable_2 와 같은 밝기 — 풀에서 제외."""
        assert "touching_1.mp3" not in DARK_BGM_FILES
        assert set(DARK_BGM_FILES) == {"touching_2.mp3", "touching_3.mp3"}

    def test_non_political_unchanged(self):
        """일반/연예 등 다른 소스는 기존 emotion 풀 그대로."""
        s = _script(source_type="blind", emotion="funny",
                    n_scenes=6, emphasis=True, duration=42.0)
        assert select_bgm_for_script(s).startswith("funny_")

    def test_celebrity_pool_still_wins(self):
        s = _script(source_type="celebrity", emotion="touching",
                    n_scenes=6, emphasis=True, duration=42.0)
        assert select_bgm_for_script(s).startswith("celebrity_")
