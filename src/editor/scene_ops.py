"""Scene operations — immutable transformations for scene editing.

All functions return new objects without mutating the input.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.analyzer.script_models import Scene, ShortsScript


class SceneOpsError(Exception):
    """Raised when a scene operation fails."""


# Priority-ordered groups for splitting text at natural boundaries.
# Sentence terminators are preferred so scenes never cut mid-sentence.
_SPLIT_PRIORITY_GROUPS: tuple[tuple[str, ...], ...] = (
    (".", "!", "?", "…"),   # sentence terminators
    (",", ";", ":", "—"),   # clause separators
    (" ", "\n"),             # whitespace
)


def _find_split_position(text: str, preferred_mid: int) -> int | None:
    """Return the character index just after a natural break closest to ``preferred_mid``.

    Priority: sentence terminator > clause separator > whitespace.
    Within each priority, the position closest to ``preferred_mid`` wins.
    Returns ``None`` if no break character is found in the interior of ``text``.
    """
    if len(text) < 4:
        return None
    preferred_mid = max(2, min(preferred_mid, len(text) - 2))

    for group in _SPLIT_PRIORITY_GROUPS:
        best: int | None = None
        best_distance = len(text) + 1
        for i, ch in enumerate(text):
            if ch not in group:
                continue
            # Split *after* the break char so the break stays with the left half.
            split_after = i + 1
            if split_after <= 2 or split_after >= len(text) - 1:
                continue
            distance = abs(split_after - preferred_mid)
            # `<=` so that on ties we prefer later positions — this keeps
            # `text_a` longer (fewer 1-word halves after strip/split).
            if distance <= best_distance:
                best = split_after
                best_distance = distance
        if best is not None:
            return best
    return None


def scene_split(
    script: ShortsScript,
    scene_id: int,
    split_position: int,
) -> ShortsScript:
    """Split a scene at the given text character position.

    Returns a new ShortsScript with the target scene replaced by two scenes.
    The split_position refers to the character index in scene.text where
    the split occurs. voice_text is split at the nearest word boundary.
    """
    target = _find_scene(script, scene_id)
    text = target.text.replace("\\n", "\n")

    if split_position <= 0 or split_position >= len(text):
        raise SceneOpsError(
            f"분할 위치가 유효하지 않습니다: {split_position} "
            f"(텍스트 길이: {len(text)})"
        )

    text_a = text[:split_position].strip()
    text_b = text[split_position:].strip()

    if len(text_a.split()) < 2 or len(text_b.split()) < 2:
        raise SceneOpsError("분할 후 각 씬에 최소 2단어 이상 필요합니다")

    voice = target.voice_text
    voice_mid = len(voice) * split_position // len(text) if len(text) else len(voice) // 2
    voice_split = _find_split_position(voice, voice_mid)
    if voice_split is None:
        # Legacy fallback: nearest whitespace to the proportional midpoint.
        space_idx = voice.rfind(" ", 0, voice_mid)
        if space_idx <= 0:
            space_idx = voice.find(" ", voice_mid)
        voice_split = space_idx if space_idx > 0 else voice_mid

    voice_a = voice[:voice_split].strip()
    voice_b = voice[voice_split:].strip()

    ratio = len(text_a) / len(text)
    dur_a = round(target.duration * ratio, 1)
    dur_b = round(target.duration - dur_a, 1)

    # Phase 3 (2026-05-20): subtitle_group_id 등 V2 필드 전파 — 안 그러면
    # split_scenes_to_max_duration이 정치_pro 씬을 자를 때 색·강조·그룹 정보가 사라짐.
    scene_a = Scene(
        id=target.id,
        timestamp=target.timestamp,
        duration=dur_a,
        type=target.type,
        text=text_a,
        voice_text=voice_a,
        emphasis=target.emphasis,
        highlight_words=tuple(w for w in target.highlight_words if w in text_a),
        visual_type=target.visual_type,
        subtitle_style=target.subtitle_style,
        transition=None,
        sfx=target.sfx,
        hook=target.hook,
        highlight_category=target.highlight_category,
        subtitle_color=target.subtitle_color,
        subtitle_emphasis=target.subtitle_emphasis,
        subtitle_group_id=target.subtitle_group_id,
        subtitle_group_first=target.subtitle_group_first,
    )
    scene_b = Scene(
        id=target.id + 1,
        timestamp=round(target.timestamp + dur_a, 1),
        duration=dur_b,
        type=target.type,
        text=text_b,
        voice_text=voice_b,
        emphasis=target.emphasis,
        highlight_words=tuple(w for w in target.highlight_words if w in text_b),
        visual_type=target.visual_type,
        subtitle_style=target.subtitle_style,
        transition=target.transition,
        hook=False,  # hook은 첫 씬만
        highlight_category=target.highlight_category,
        subtitle_color=target.subtitle_color,
        subtitle_emphasis=target.subtitle_emphasis,
        # 그룹 있으면 이어받지만 항상 group_first=False (연속 씬). 그룹 없으면 default(None/True).
        subtitle_group_id=target.subtitle_group_id,
        subtitle_group_first=(False if target.subtitle_group_id is not None else True),
    )

    new_scenes = []
    for s in script.scenes:
        if s.id == scene_id:
            new_scenes.append(scene_a)
            new_scenes.append(scene_b)
        elif s.id > scene_id:
            new_scenes.append(Scene(
                id=s.id + 1,
                timestamp=round(s.timestamp + dur_a - target.duration + dur_b - (target.duration - dur_a), 1)
                if s.id == scene_id + 1
                else s.timestamp,
                duration=s.duration,
                type=s.type,
                text=s.text,
                voice_text=s.voice_text,
                emphasis=s.emphasis,
                highlight_words=s.highlight_words,
                visual_type=s.visual_type,
                motion_prompt=s.motion_prompt,
                subtitle_style=s.subtitle_style,
                transition=s.transition,
                sfx=s.sfx,
            ))
        else:
            new_scenes.append(s)

    new_scenes = _recalculate_timestamps(new_scenes)
    return _rebuild_script(script, new_scenes)


def scene_merge(
    script: ShortsScript,
    scene_id_1: int,
    scene_id_2: int,
) -> ShortsScript:
    """Merge two adjacent scenes into one.

    Returns a new ShortsScript with the two scenes replaced by a single merged scene.
    """
    s1 = _find_scene(script, scene_id_1)
    s2 = _find_scene(script, scene_id_2)

    merged_text = f"{s1.text}\n{s2.text}"
    if len(merged_text.replace('\n', '')) > 60:
        raise SceneOpsError(
            f"병합 후 텍스트가 너무 깁니다 ({len(merged_text.replace(chr(10), ''))}자). "
            "45자 이내를 권장합니다."
        )

    merged = Scene(
        id=s1.id,
        timestamp=s1.timestamp,
        duration=round(s1.duration + s2.duration, 1),
        type=s1.type,
        text=merged_text,
        voice_text=f"{s1.voice_text} {s2.voice_text}",
        emphasis=s1.emphasis if s1.emphasis == "high" else s2.emphasis,
        highlight_words=s1.highlight_words + s2.highlight_words,
        visual_type=s1.visual_type,
        subtitle_style=s1.subtitle_style,
        transition=s2.transition,
        sfx=s1.sfx + s2.sfx,
    )

    new_scenes = []
    skip_next = False
    for s in script.scenes:
        if skip_next:
            skip_next = False
            continue
        if s.id == scene_id_1:
            new_scenes.append(merged)
            skip_next = True
        else:
            new_scenes.append(s)

    new_scenes = _renumber_scenes(new_scenes)
    new_scenes = _recalculate_timestamps(new_scenes)
    return _rebuild_script(script, new_scenes)


def scene_delete(
    script: ShortsScript,
    scene_id: int,
) -> ShortsScript:
    """Remove a scene from the script.

    Returns a new ShortsScript with the scene removed and remaining scenes
    renumbered and timestamps recalculated. Raises SceneOpsError if only
    one scene remains or the scene_id does not exist.
    """
    if len(script.scenes) <= 1:
        raise SceneOpsError("마지막 씬은 삭제할 수 없습니다")
    _find_scene(script, scene_id)  # raises if not found

    new_scenes = [s for s in script.scenes if s.id != scene_id]
    new_scenes = _renumber_scenes(new_scenes)
    new_scenes = _recalculate_timestamps(new_scenes)
    return _rebuild_script(script, new_scenes)


def scene_reorder(
    script: ShortsScript,
    new_order: list[int],
) -> ShortsScript:
    """Reorder scenes by their IDs.

    new_order is a list of scene IDs in the desired order.
    Returns a new ShortsScript with scenes reordered and timestamps recalculated.
    """
    scene_map = {s.id: s for s in script.scenes}
    reordered = []
    for sid in new_order:
        if sid not in scene_map:
            raise SceneOpsError(f"씬 ID {sid}를 찾을 수 없습니다")
        reordered.append(scene_map[sid])

    reordered = _renumber_scenes(reordered)
    reordered = _recalculate_timestamps(reordered)
    return _rebuild_script(script, reordered)


def scene_resize(
    script: ShortsScript,
    scene_id: int,
    new_duration: float,
) -> ShortsScript:
    """Change a scene's duration and adjust subsequent timestamps.

    Returns a new ShortsScript with the modified duration.
    """
    if new_duration < 1.0:
        raise SceneOpsError("씬 길이는 최소 1초 이상이어야 합니다")
    if new_duration > 30.0:
        raise SceneOpsError("씬 길이는 최대 30초까지 가능합니다")

    new_scenes = []
    for s in script.scenes:
        if s.id == scene_id:
            new_scenes.append(Scene(
                id=s.id,
                timestamp=s.timestamp,
                duration=round(new_duration, 1),
                type=s.type,
                text=s.text,
                voice_text=s.voice_text,
                emphasis=s.emphasis,
                highlight_words=s.highlight_words,
                visual_type=s.visual_type,
                motion_prompt=s.motion_prompt,
                subtitle_style=s.subtitle_style,
                transition=s.transition,
                sfx=s.sfx,
            ))
        else:
            new_scenes.append(s)

    new_scenes = _recalculate_timestamps(new_scenes)
    return _rebuild_script(script, new_scenes)


def update_script_file(script: ShortsScript, script_path: str | Path) -> str:
    """Save updated script to file and return the path."""
    path = Path(script_path)
    path.write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(path)


def _find_scene(script: ShortsScript, scene_id: int) -> Scene:
    for s in script.scenes:
        if s.id == scene_id:
            return s
    raise SceneOpsError(f"씬 ID {scene_id}를 찾을 수 없습니다")


def _renumber_scenes(scenes: list[Scene]) -> list[Scene]:
    result = []
    for i, s in enumerate(scenes):
        result.append(Scene(
            id=i + 1,
            timestamp=s.timestamp,
            duration=s.duration,
            type=s.type,
            text=s.text,
            voice_text=s.voice_text,
            emphasis=s.emphasis,
            highlight_words=s.highlight_words,
            visual_type=s.visual_type,
            motion_prompt=s.motion_prompt,
            subtitle_style=s.subtitle_style,
            transition=s.transition,
            sfx=s.sfx,
        ))
    return result


def _recalculate_timestamps(scenes: list[Scene]) -> list[Scene]:
    result = []
    cursor = 0.0
    for s in scenes:
        result.append(Scene(
            id=s.id,
            timestamp=round(cursor, 1),
            duration=s.duration,
            type=s.type,
            text=s.text,
            voice_text=s.voice_text,
            emphasis=s.emphasis,
            highlight_words=s.highlight_words,
            visual_type=s.visual_type,
            motion_prompt=s.motion_prompt,
            subtitle_style=s.subtitle_style,
            transition=s.transition,
            sfx=s.sfx,
        ))
        cursor += s.duration
    return result


def _rebuild_script(original: ShortsScript, new_scenes: list[Scene]) -> ShortsScript:
    total_dur = sum(s.duration for s in new_scenes)
    tts_script = " ".join(s.voice_text for s in new_scenes if s.voice_text.strip())
    return ShortsScript(
        metadata=original.metadata,
        scenes=tuple(new_scenes),
        audio=AudioConfig(
            tts_script=tts_script,
            voice=original.audio.voice,
            rate=original.audio.rate,
            pitch=original.audio.pitch,
        ),
        background=original.background,
    )


from src.analyzer.script_models import AudioConfig


def split_scenes_to_max_duration(
    script: ShortsScript, max_duration: float | None = None
) -> ShortsScript:
    """Iteratively split any scene whose duration exceeds ``max_duration``.

    This is a safety net for scripts produced before the analyzer enforced
    per-scene duration limits. Long scenes are split at the middle of their
    display text (roughly). Repeated until every scene is ≤ ``max_duration``.

    Why this matters: video generation models like Kling 2.5 produce fixed
    5-second clips. A 10-second scene with a 5-second video freezes for the
    last 5 seconds on the last frame, creating a visible pause.

    Args:
        script: The ShortsScript to process.
        max_duration: Maximum seconds per scene. Defaults to
            ``settings.MAX_SCENE_DURATION_SECONDS`` (5.0).

    Returns:
        A new ShortsScript where every scene.duration ≤ max_duration.
    """
    from src.config.settings import MAX_SCENE_DURATION_SECONDS

    limit = max_duration if max_duration is not None else MAX_SCENE_DURATION_SECONDS
    if limit <= 0:
        raise SceneOpsError(f"max_duration must be positive, got {limit}")

    result = script
    # Iterate until no further splits are possible. Hard-cap at 100 rounds to
    # prevent infinite loops on pathological inputs.
    for _ in range(100):
        # Find the first scene that's still too long
        target = next(
            (s for s in result.scenes if s.duration > limit), None
        )
        if target is None:
            return result  # All scenes fit within the limit

        # Split at the middle of the display text
        text = target.text.replace("\\n", "\n")
        if len(text) < 4:
            # Too short to split meaningfully — give up on this scene
            break

        # Prefer sentence terminators; fall back to clause separators, then whitespace.
        snapped = _find_split_position(text, len(text) // 2)
        split_pos = snapped if snapped is not None else len(text) // 2

        try:
            result = scene_split(result, target.id, split_pos)
        except SceneOpsError:
            # Split failed (e.g., too few words) — stop to avoid infinite loop
            break

    return result
