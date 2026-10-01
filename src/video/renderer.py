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
# 041: 인물 배지(우상단 1줄) 상한 — 넘기면 인물 화면을 가린다.
PERSON_BADGE_MAX_LEN = 40


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
    headline_font: str = "",
    headline_letter_spacing: int = 0,
    person_badge: str = "",
    respect_background_colors: bool = False,
    headline_color: str = "",
    overlay_boxes: bool = True,
    headline_plain: bool = False,
    badge_boxed: bool | None = None,
    news_card: dict | None = None,
    evidence_layer: dict | None = None,
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
        headline_plain: 042 V4.0 — 커스텀 서체 헤드라인의 외곽선·그림자를 끈다.
        badge_boxed: 042 V4.0 — 배지 박스를 제목 박스(overlay_boxes)와 따로 정한다.
                  None 이면 overlay_boxes 를 따른다(041 동작).
        news_card: 042 V4.0 사진 슬라이드 — {photos:[{path,fit,start_ms,end_ms}],
                  captions:[{text,start_ms,end_ms,hl,color}], credit_line, font_family}.
                  지정 시 씬별 비주얼 대신 NewsCardLayer 가 사진·자막·출처를 그린다.
        evidence_layer: 043 V5.0 증거 삽입형 — {headline, headline_colors, captions,
                  pops, evidence:[{path,start_ms,end_ms,marks}], flashes, channel_label,
                  source_label, font_family}. 지정 시 씬 영상은 미디어 박스에만 깔리고
                  헤드라인·자막·증거 카드는 EvidenceLayer 가 그린다.
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

    # 042 V4.0 뉴스 카드 사진 — 렌더 전 fail-fast (빠진 사진은 빈 박스로 렌더된다)
    news_card_props = None
    if news_card:
        news_card_props = _news_card_props(news_card, public_dir, timestamp, temp_files)

    # 043 V5.0 증거 카드 캡처 — 렌더 전 fail-fast (042 와 같은 이유)
    evidence_props = None
    if evidence_layer:
        evidence_props = _evidence_layer_props(evidence_layer, public_dir, timestamp,
                                               temp_files)

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
        # 041 V3.0 옵트인 — 미지정이면 037 규격(Noto Sans KR 100px) 그대로.
        "headlineFont": headline_font,
        "headlineLetterSpacing": headline_letter_spacing,
        # 인물 배지는 우상단 한 줄이라 길면 화면을 가린다.
        "personBadge": (person_badge or "").strip()[:PERSON_BADGE_MAX_LEN],
        # political_pro/celebrity 는 배경을 검정으로 강제한다(씬 사이 깜빡임에
        # 그라데이션이 비치는 문제). 명시 옵트인일 때만 script.background.colors 를
        # 그대로 쓴다 — bg_colors 를 적어 둔 기존 config 10개의 동작을 보존한다.
        "respectBackgroundColors": respect_background_colors,
        # 헤드라인 1열 글자색. "" 면 기존 흰색(037 규격).
        "headlineColor": headline_color,
        # 제목·인물 배지의 반투명 검정 박스. 밝은 캔버스에서는 회색으로 보이므로
        # 끄고 글자색만으로 대비를 만든다.
        "overlayBoxes": overlay_boxes,
        "headlinePlain": headline_plain,
        "badgeBoxed": badge_boxed,
    }
    if news_card_props is not None:
        props["newsCard"] = news_card_props
        # 출처 줄은 카드가 자기 위치·스타일로 그린다 — 기본 박스 라벨과 중복 금지.
        props["sourceLabel"] = ""
    if evidence_props is not None:
        props["evidenceLayer"] = evidence_props
        # 출처는 레이어가 우상단에 그린다 — 하단 기본 박스 라벨과 중복 금지.
        props["sourceLabel"] = ""

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


def _news_card_props(card: dict, public_dir: Path, timestamp: str,
                     temp_files: list[Path]) -> dict:
    """042 V4.0 — 사진을 public/ 으로 복사하고 Remotion camelCase 프롭을 만든다."""
    # 복사 전에 전부 확인한다 — 여기서의 예외는 렌더 try/finally 정리 구간보다
    # 앞이라, 중간에 멈추면 먼저 복사한 사진이 public/ 에 남는다.
    missing = [p["path"] for p in card.get("photos") or [] if not Path(p["path"]).exists()]
    if missing:
        raise FileNotFoundError(f"뉴스 카드 사진 없음: {', '.join(missing)}")
    photos = []
    for i, p in enumerate(card.get("photos") or []):
        src = Path(p["path"])
        name = f"news_{timestamp}_{i:02d}{src.suffix.lower() or '.jpg'}"
        shutil.copy2(src, public_dir / name)
        temp_files.append(public_dir / name)
        photos.append({"file": name, "fit": p.get("fit", "cover"),
                       "startMs": int(p["start_ms"]), "endMs": int(p["end_ms"])})
    captions = [
        {"text": c["text"], "startMs": int(c["start_ms"]), "endMs": int(c["end_ms"]),
         "hl": list(c.get("hl") or []), "color": c.get("color", "white")}
        for c in card.get("captions") or []
    ]
    return {
        "photos": photos,
        "captions": captions,
        "creditLine": card.get("credit_line", ""),
        "fontFamily": card.get("font_family", ""),
    }


def _evidence_layer_props(layer: dict, public_dir: Path, timestamp: str,
                          temp_files: list[Path]) -> dict:
    """043 V5.0 — 증거 캡처를 public/ 으로 복사하고 Remotion camelCase 프롭을 만든다."""
    evidence = layer.get("evidence") or []
    missing = [e["path"] for e in evidence if not Path(e["path"]).exists()]
    if missing:
        raise FileNotFoundError(f"증거 캡처 없음: {', '.join(missing)}")
    cards = []
    for i, e in enumerate(evidence):
        src = Path(e["path"])
        name = f"evid_{timestamp}_{i:02d}{src.suffix.lower() or '.png'}"
        shutil.copy2(src, public_dir / name)
        temp_files.append(public_dir / name)
        cards.append({"file": name, "startMs": int(e["start_ms"]),
                      "endMs": int(e["end_ms"]),
                      "marks": [dict(m) for m in e.get("marks") or []]})
    return {
        "headline": list(layer.get("headline") or []),
        "headlineColors": list(layer.get("headline_colors") or []),
        "captions": [{"text": c["text"], "startMs": int(c["start_ms"]),
                      "endMs": int(c["end_ms"]), "hl": list(c.get("hl") or [])}
                     for c in layer.get("captions") or []],
        "pops": [{"text": p["text"], "startMs": int(p["start_ms"]),
                  "endMs": int(p["end_ms"])} for p in layer.get("pops") or []],
        "evidence": cards,
        "flashesMs": [int(ms) for ms in layer.get("flashes") or []],
        "framing": [{"sceneId": int(f["scene_id"]), "zoom": float(f.get("zoom", 1.0)),
                     "focusX": float(f.get("focus_x", 0.5))}
                    for f in layer.get("framing") or []],
        "channelLabel": layer.get("channel_label", ""),
        "sourceLabel": layer.get("source_label", ""),
        "fontFamily": layer.get("font_family", ""),
    }


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
