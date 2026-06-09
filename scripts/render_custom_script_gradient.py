"""Render a pre-built ShortsScript JSON with gradient background only.

No source video clip — uses the gradient defined in script.background. Faster
alternative to ``render_custom_script_edge.py`` when no usable source clip is
available (e.g. all candidate YouTube videos are too long to download).

Usage:
    python3 scripts/render_custom_script_gradient.py \
        <script_path>

Example:
    python3 scripts/render_custom_script_gradient.py \
        data/political_pro/20260604_oh_sehoon_comeback/script_plan_oh_comeback.json
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    script_path = Path(sys.argv[1]).resolve()
    if not script_path.exists():
        print(f"❌ script not found: {script_path}", file=sys.stderr)
        return 4

    from src.analyzer.script_models import AudioConfig, ShortsScript

    script = ShortsScript.load(script_path)
    print(f"✅ 스크립트 로드: {script_path.name} "
          f"({len(script.scenes)}씬, {script.metadata.duration}초)",
          file=sys.stderr)

    # 락인 포맷: InJoonNeural +22% (정치 쇼츠 검증 포맷)
    script = ShortsScript(
        metadata=script.metadata,
        scenes=script.scenes,
        audio=AudioConfig(
            tts_script=script.audio.tts_script,
            voice="ko-KR-InJoonNeural",
            rate="+22%",
            pitch=script.audio.pitch,
        ),
        background=script.background,
    )
    print(f"   voice={script.audio.voice} rate={script.audio.rate} "
          f"bg={script.background.type}({len(script.background.colors)}색)",
          file=sys.stderr)

    # Edge TTS
    print(f"🎙️ Edge TTS (InJoonNeural +22%) 합성 중...", file=sys.stderr)
    from src.tts.edge_tts_generator import generate_voice_with_timing

    audio_path, timings = generate_voice_with_timing(script)
    print(f"✅ 음성 합성 완료: {audio_path}", file=sys.stderr)

    # Sanity check
    import subprocess

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(audio_path)],
        capture_output=True, text=True,
    )
    audio_dur = float(probe.stdout.strip())
    print(f"📊 오디오 길이: {audio_dur:.1f}s "
          f"(목표 ~{script.metadata.duration}s)", file=sys.stderr)

    # Remotion render — no scene_videos → gradient background
    print(f"🎬 Remotion 렌더 중 (그라데이션 배경)...", file=sys.stderr)
    from src.video.renderer import render_video

    mp4 = render_video(
        script,
        audio_path=audio_path,
        scene_videos=None,
        use_bgm=False,
        scene_timings=timings,
        enable_transitions=False,
        enable_sfx=False,
    )

    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, "
          f"{script.metadata.duration:.0f}s)", file=sys.stderr)
    print(str(mp4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
