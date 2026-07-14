"""Remotion video renderer — generates MP4 from ShortsScript + audio + images.

Calls Remotion CLI via subprocess to render the final video.
Constitution Principle III: Text-First Video.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from src.analyzer.script_models import ShortsScript
from src.config.settings import DATA_AUDIO_DIR, PROJECT_ROOT
from src.upload.thumbnail_generator import generate_thumbnail_from_script
from src.video.bgm_matcher import find_hook_scene, intro_bgm_for_emotion
from src.video.sfx_matcher import auto_assign_sfx
from src.video.transition_matcher import auto_assign_transitions

logger = logging.getLogger(__name__)

DATA_OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
REMOTION_DIR = PROJECT_ROOT / "src" / "video" / "remotion"
FPS = 30


class RenderError(Exception):
    """Raised when video rendering fails."""


def _strip_scene_effects(
    script: ShortsScript,
    *,
    drop_sfx: bool,
    drop_transitions: bool,
) -> ShortsScript:
    """Return a new ShortsScript with ``sfx`` and/or ``transition`` cleared.

    Scenes are frozen dataclasses, so this produces a fresh script object;
    the input is never mutated. Used when the user disables transition
    effects or sound effects from the UI.
    """
    if not drop_sfx and not drop_transitions:
        return script
    from dataclasses import replace
    new_scenes = tuple(
        replace(
            sc,
            sfx=() if drop_sfx else sc.sfx,
            transition=None if drop_transitions else sc.transition,
        )
        for sc in script.scenes
    )
    return replace(script, scenes=new_scenes)


def render_video(
    script: ShortsScript,
    audio_path: Path | None = None,
    scene_images: list[dict] | None = None,
    scene_videos: list[dict] | None = None,
    output_dir: Path | None = None,
    use_bgm: bool = True,
    use_intro_bgm: bool = True,
    scene_timings: list[dict] | None = None,
    auto_sfx: bool = True,
    auto_transition: bool = True,
    auto_thumbnail: bool = True,
    enable_sfx: bool = True,
    enable_transitions: bool = True,
    speed_multiplier: float = 1.0,
    background_video: Path | None = None,
) -> Path:
    """Render a ShortsScript into an MP4 video.

    Args:
        script: The ShortsScript to render
        audio_path: Path to voice MP3 file
        scene_images: List of {scene_id, image_path} dicts for manga backgrounds
        scene_videos: List of {scene_id, video_path} dicts for AI video clips
        output_dir: Output directory (defaults to data/outputs/)
        use_bgm: Whether to include background music
        scene_timings: Per-scene TTS timing data for audio-video sync
        auto_sfx: QW-04 — auto-assign whoosh/impact SFX to every cut transition.
                  Pass False to keep original scene.sfx (or no SFX at all).
        auto_transition: QW-06 — auto-assign 0.2s punch-zoom to high-emphasis
                  and hook scenes. Pass False to keep original transitions.
        enable_sfx: User-level switch. When False, ALL scene SFX are removed
                  (including analyzer-generated and auto-assigned) and auto_sfx
                  is forced off. Default True preserves existing behavior.
        enable_transitions: User-level switch. When False, ALL scene transitions
                  are cleared and auto_transition is forced off. Default True.
        background_video: 단일 연속 배경 영상 경로. 지정 시 콘텐츠 전체 구간에
                  한 번만 마운트되는 OffthreadVideo로 깔리며, 씬별 자막은
                  텍스트 오버레이로만 렌더됨 (씬별 클립 끊김 제거).
    """
    # SFX globally disabled (2026-06-12) — UI 토글·CLI 인자와 무관하게 항상 OFF.
    # 데이터 모델(`SfxConfig`, `Scene.sfx`)·자동 할당 모듈(`sfx_matcher.py`)·에셋
    # (`data/sfx/`, `public/sfx/`)·테스트는 보존되어 있어 향후 재활성화 시 본 라인만
    # 제거하면 됨. 자세한 결정 배경은 prompt_plan.md 참조.
    enable_sfx = False
    auto_sfx = False
    # User-disabled effects take priority over auto-assignment.
    if not enable_transitions:
        auto_transition = False

    # QW-04: 모든 컷 전환에 whoosh/impact SFX 자동 주입 (사용자 지정 sfx 는 보존).
    if auto_sfx:
        script = auto_assign_sfx(script)

    # QW-06: high emphasis + hook 씬에 punch-zoom 트랜지션 자동 주입.
    if auto_transition:
        script = auto_assign_transitions(script)

    # Finally, strip any remaining effects the user opted out of.
    script = _strip_scene_effects(
        script,
        drop_sfx=not enable_sfx,
        drop_transitions=not enable_transitions,
    )

    target_dir = output_dir or DATA_OUTPUTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(
        c for c in script.metadata.title[:30] if c.isalnum() or c in " _-"
    )
    safe_title = safe_title.strip().replace(" ", "_") or "untitled"
    output_filename = f"{timestamp}_{safe_title}.mp4"
    output_path = target_dir / output_filename

    base_duration = script.metadata.duration
    outro_seconds = 4  # Subscribe/like/bell outro
    duration_frames = int((base_duration + outro_seconds) * FPS)

    # Copy assets to Remotion public dir for staticFile() access
    public_dir = PROJECT_ROOT / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    temp_files: list[Path] = []

    # Audio
    audio_filename = ""
    if audio_path and audio_path.exists():
        audio_filename = f"audio_{timestamp}.mp3"
        shutil.copy2(audio_path, public_dir / audio_filename)
        temp_files.append(public_dir / audio_filename)

    # Scene images
    scene_image_props = []
    if scene_images:
        for img_data in scene_images:
            src_path = Path(img_data["image_path"])
            if src_path.exists():
                img_filename = f"img_{timestamp}_scene_{img_data['scene_id']:02d}.png"
                shutil.copy2(src_path, public_dir / img_filename)
                temp_files.append(public_dir / img_filename)
                scene_image_props.append({
                    "sceneId": img_data["scene_id"],
                    "imageFile": img_filename,
                })

    # Continuous background video (단일 연속 클립 — 씬별 컷 끊김 제거용).
    background_video_filename = ""
    if background_video and Path(background_video).exists():
        background_video_filename = f"bgvid_{timestamp}.mp4"
        shutil.copy2(background_video, public_dir / background_video_filename)
        temp_files.append(public_dir / background_video_filename)
        logger.info("연속 배경 영상 적용: %s", background_video.name)

    # Scene videos (AI video clips)
    scene_video_props = []
    if scene_videos:
        for vid_data in scene_videos:
            src_path = Path(vid_data["video_path"])
            if src_path.exists():
                vid_filename = f"vid_{timestamp}_scene_{vid_data['scene_id']:02d}.mp4"
                shutil.copy2(src_path, public_dir / vid_filename)
                temp_files.append(public_dir / vid_filename)
                scene_video_props.append({
                    "sceneId": vid_data["scene_id"],
                    "videoFile": vid_filename,
                })

    # BGM
    bgm_filename = ""
    if use_bgm:
        from src.tts.voice_config import select_bgm_for_script
        bgm_src = PROJECT_ROOT / "data" / "bgm" / select_bgm_for_script(script)
        if bgm_src.exists():
            bgm_filename = f"bgm_{timestamp}.mp3"
            shutil.copy2(bgm_src, public_dir / bgm_filename)
            temp_files.append(public_dir / bgm_filename)
            logger.info("BGM 적용: %s (%s)", bgm_src.name, script.metadata.emotion_type)
        else:
            logger.warning("BGM 파일 없음: %s — BGM 없이 진행", bgm_src)

    # QW-07: hook 씬에 인트로 빌드업 BGM 자동 매칭. public/bgm/ 에 사전
    # 수집된 트랙을 staticFile() 로 직접 로드 (별도 복사 불필요).
    intro_bgm_filename = ""
    if use_intro_bgm and find_hook_scene(script) is not None:
        track = intro_bgm_for_emotion(script.metadata.emotion_type)
        track_path = PROJECT_ROOT / "public" / "bgm" / track
        if track_path.exists():
            intro_bgm_filename = track
            logger.info("Hook 인트로 BGM 적용: %s", track)
        else:
            logger.warning("Hook 인트로 BGM 누락: %s", track_path)

    # Copy SFX files to public dir for Remotion staticFile() access
    sfx_dir = PROJECT_ROOT / "data" / "sfx"
    for scene in script.scenes:
        for sfx in (scene.sfx or ()):
            sfx_src = sfx_dir / (sfx.name + ".mp3")
            if sfx_src.exists():
                sfx_dst = public_dir / (sfx.name + ".mp3")
                if not sfx_dst.exists():
                    shutil.copy2(sfx_src, sfx_dst)
                    temp_files.append(sfx_dst)

    script_dict = _convert_to_camel_case(script.to_dict())

    # Apply scene timings from per-scene TTS (most accurate)
    if scene_timings:
        timing_map = {t["scene_id"]: t for t in scene_timings if t["scene_id"] != -1}
        outro_timing = next((t for t in scene_timings if t["scene_id"] == -1), None)

        for scene in script_dict["scenes"]:
            sid = scene["id"]
            if sid in timing_map:
                t = timing_map[sid]
                scene["timestamp"] = t["start_ms"] / 1000.0
                scene["duration"] = (t["end_ms"] - t["start_ms"]) / 1000.0

        # Content ends when last non-outro scene's audio ends
        last_content = max(
            (t for t in scene_timings if t["scene_id"] != -1),
            key=lambda x: x["end_ms"],
            default=None,
        )
        content_end_s = last_content["end_ms"] / 1000.0 if last_content else base_duration
        script_dict["metadata"]["duration"] = content_end_s

        # Outro comes right after content, lasts at least 4 seconds
        outro_dur_s = 4.0
        if outro_timing:
            outro_dur_s = max((outro_timing["end_ms"] - outro_timing["start_ms"]) / 1000.0 + 1.0, 4.0)

        total_video_dur = content_end_s + outro_dur_s
        duration_frames = int(total_video_dur * FPS)

        logger.info("TTS 타이밍: %d씬, content=%.1fs, outro=%.1fs, total=%.1fs",
                     len(timing_map), content_end_s, outro_dur_s, total_video_dur)
    else:
        # Fallback: measure actual audio duration and rescale
        actual_audio_dur = _get_audio_duration(audio_path) if audio_path and audio_path.exists() else None
        if actual_audio_dur and actual_audio_dur > 0:
            script_total = script.metadata.duration
            if script_total > 0:
                ratio = actual_audio_dur / script_total
                logger.info("타이밍 보정 (비율): %.1fs → %.1fs (%.2f)", script_total, actual_audio_dur, ratio)
                base_duration = actual_audio_dur
                duration_frames = int((actual_audio_dur + outro_seconds) * FPS)
                script_dict["metadata"]["duration"] = actual_audio_dur
                for scene in script_dict["scenes"]:
                    scene["timestamp"] = scene["timestamp"] * ratio
                    scene["duration"] = scene["duration"] * ratio
        else:
            script_dict["metadata"]["duration"] = base_duration

    # 화면 하단에 출처 표시.
    # 우선순위: 1) metadata.source_label (명시적 — 복수 출처 등 자유 텍스트),
    #          2) source_channel + source_title (political_pro 자동 생성),
    #          3) source_url 폴백.
    # political / political_pro / topic 모드 모두 적용.
    source_label = ""
    explicit_label = (script.metadata.source_label or "").strip()
    if explicit_label:
        # 명시적 라벨은 그대로 사용. 너무 길면 잘라냄 (총 80자).
        source_label = explicit_label[:80]
    elif script.metadata.source_type in ("political", "political_pro"):
        ch = (script.metadata.source_channel or "").strip()
        ti = (script.metadata.source_title or "").strip()
        if ch and ti:
            max_title = max(20, 60 - len(ch) - 6)
            short_ti = ti if len(ti) <= max_title else ti[:max_title - 1] + "…"
            source_label = f"출처: {ch} : {short_ti}"
        elif ch:
            source_label = f"출처: {ch}"
        elif ti:
            source_label = f"출처: {ti}"
        elif script.metadata.source_url:
            url = script.metadata.source_url
            compact = url.replace("https://", "").replace("http://", "").replace("www.", "")
            source_label = f"출처: {compact}"

    props = {
        "scriptData": script_dict,
        "audioFile": audio_filename,
        "sceneImages": scene_image_props,
        "sceneVideos": scene_video_props,
        "bgmFile": bgm_filename,
        "introBgmFile": intro_bgm_filename,
        "sourceLabel": source_label,
        "backgroundVideoFile": background_video_filename,
    }

    props_path = target_dir / f"{timestamp}_props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    img_count = len(scene_image_props)
    vid_count = len(scene_video_props)
    logger.info(
        "렌더링 시작: %s (%d프레임, %.1f초, 이미지 %d장, 비디오 %d개)",
        output_filename, duration_frames, base_duration, img_count, vid_count,
    )

    npx_path = shutil.which("npx")
    if not npx_path:
        raise RenderError("npx를 찾을 수 없습니다. Node.js가 설치되어 있는지 확인하세요.")

    cmd = [
        npx_path, "remotion", "render",
        str(REMOTION_DIR / "src" / "index.ts"),
        "BlindShorts",
        str(output_path),
        "--props", str(props_path),
        "--frames", f"0-{duration_frames - 1}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30분 — 많은 씬 + 비디오 배경 렌더는 오래 걸림
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        raise RenderError("렌더링 시간 초과 (30분).")
    finally:
        if props_path.exists():
            props_path.unlink()
        for f in temp_files:
            if f.exists():
                f.unlink()

    if result.returncode != 0:
        error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
        raise RenderError(f"Remotion 렌더링 실패 (exit {result.returncode}):\n{error_msg}")

    if not output_path.exists():
        raise RenderError(f"렌더링 완료되었으나 출력 파일이 없습니다: {output_path}")

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("렌더링 완료: %s (%.1f MB)", output_path, file_size_mb)

    if auto_thumbnail:
        try:
            thumb = generate_thumbnail_from_script(script, output_path, target_dir)
            logger.info("썸네일 생성 완료: %s", thumb)
        except Exception as exc:
            logger.warning("썸네일 생성 실패 (비치명적): %s", exc)

    if speed_multiplier != 1.0:
        output_path = _apply_speed(output_path, speed_multiplier)

    return output_path


def _apply_speed(input_path: Path, multiplier: float) -> Path:
    """ffmpeg으로 영상 + 오디오를 multiplier 배속으로 처리. 원본 파일 덮어씀."""
    tmp_path = input_path.with_suffix(".speed_tmp.mp4")
    pts = 1.0 / multiplier  # setpts: PTS/multiplier
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-filter_complex",
        f"[0:v]setpts={pts:.6f}*PTS[v];[0:a]atempo={multiplier:.2f}[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast",
        "-loglevel", "error",
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RenderError(
            f"영상 배속 처리 실패 (exit {result.returncode}): {(result.stderr or '')[:200]}"
        )
    tmp_path.replace(input_path)
    logger.info("%.1fx 배속 처리 완료: %s", multiplier, input_path.name)
    return input_path


def _convert_to_camel_case(data):
    """Convert snake_case keys to camelCase for Remotion props."""
    if isinstance(data, dict):
        return {_snake_to_camel(k): _convert_to_camel_case(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_to_camel_case(item) for item in data]
    return data


def _snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _get_audio_duration(audio_path: Path) -> float | None:
    """Get audio duration in seconds using ffprobe.

    HyunsuMultilingualNeural outputs MPEG1 Layer3; the old bitrate-estimation
    approach returned ~50% of actual duration for that encoding.
    """
    import json
    import subprocess

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_entries", "format=duration",
                "-i", str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        info = json.loads(result.stdout)
        duration = float(info["format"]["duration"])
        logger.info("오디오 길이: %.1fs (ffprobe)", duration)
        return duration
    except Exception as e:
        logger.warning("오디오 길이 측정 실패: %s", e)
        return None
