"""Next.js API 라우트 → Python 브릿지 (Feature 027 Phase 4).

Next.js에서 `python3 -m src.jpolitics.api_bridge <command> [options]` 형태로
호출된다. 각 함수는 마지막 stdout 줄에 결과 JSON을 출력한다.
진행 메시지는 stderr로만 전송한다.

격리 boundary: V1/V2 모듈은 read-only import 전용.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# read-only imports — 모듈 수준 선언으로 테스트에서 patch 가능
from src.scraper.youtube_downloader import (
    TranscriptUnavailableError,
    download_video,
    get_video_metadata,
    transcribe_video_or_fallback,
)
from src.jpolitics.analyzer.moment_detector import (
    MomentDetectError,
    detect_moments_from_transcript,
    detect_moments_from_video,
)
from src.jpolitics.analyzer.meta_generator import generate_meta
from src.jpolitics.models.moment import MomentDetectionResult
from src.jpolitics.models.clip import CaptionCue, ClipResult
from src.jpolitics.video.clip_maker import ClipMakeError, make_moment_clip
from src.jpolitics.video.captions import build_caption_cues, save_caption_cues
from src.jpolitics.video.renderer import RenderError, render_moment_short
from src.jpolitics.constants import JPOLITICS_DATA_DIR


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _slugify(title: str, max_len: int = 24) -> str:
    slug = re.sub(r"[^\w가-힣]+", "_", title).strip("_")
    return slug[:max_len] or "video"


def _progress(msg: str) -> None:
    """진행 메시지는 stderr로만."""
    print(msg, file=sys.stderr, flush=True)


def _emit(data: dict) -> None:
    """결과 JSON을 stdout 마지막 줄에 출력."""
    print(json.dumps(data, ensure_ascii=False), flush=True)


# ── Phase 1: detect ───────────────────────────────────────────────────────────

def api_detect(url: str, no_multimodal: bool = False) -> None:
    """YouTube URL → 모먼트 검출 → stdout 마지막 줄에 JSON 출력.

    Output JSON::

        {
          "work_dir": "/path/to/...",
          "moments": [...],      # Moment.to_dict() list (확신도 내림차순)
          "channel": "YTN",
          "video_title": "..."
        }
    """
    _progress(f"📥 영상 메타데이터 조회: {url}")
    meta = get_video_metadata(url)
    title = meta.get("title") or "untitled"
    channel = meta.get("channel") or meta.get("uploader") or ""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = JPOLITICS_DATA_DIR / f"{ts}_{_slugify(title)}"
    work_dir.mkdir(parents=True, exist_ok=True)

    _progress(f"📥 영상 다운로드 중... ({title})")
    video_path = download_video(url, work_dir)

    moments = []
    detector = ""

    if not no_multimodal:
        _progress("🔍 Gemini 멀티모달 모먼트 검출 중...")
        try:
            moments = detect_moments_from_video(video_path)
            detector = "gemini_multimodal"
        except MomentDetectError as exc:
            _progress(f"⚠️  멀티모달 실패 — transcript 폴백: {exc}")

    if not moments:
        _progress("🔍 transcript 기반 모먼트 검출 중 (폴백)...")
        try:
            segments = transcribe_video_or_fallback(
                url=url, video_path=video_path, out_dir=work_dir
            )
        except TranscriptUnavailableError as exc:
            raise RuntimeError(f"transcript 확보 실패: {exc}") from exc
        moments = detect_moments_from_transcript(segments)
        detector = "transcript"

    result = MomentDetectionResult(
        source_url=url,
        video_title=title,
        channel=channel,
        detector=detector,
        moments=tuple(moments),
    )
    result.save(work_dir / "moments.json")

    sorted_moments = list(result.top(len(result.moments)))
    _emit({
        "work_dir": str(work_dir),
        "moments": [m.to_dict() for m in sorted_moments],
        "channel": channel,
        "video_title": title,
    })


# ── Phase 2: cut ──────────────────────────────────────────────────────────────

def api_cut(
    work_dir: str,
    moment_idx: int,
    crop_x: float = 0.5,
    pad: float = 0.5,
) -> None:
    """모먼트 클립 컷 + 자막 큐 생성 → stdout 마지막 줄에 JSON 출력.

    Args:
        work_dir: detect 단계에서 생성된 작업 디렉터리 경로.
        moment_idx: 0-based 인덱스 (순위 1 → 0).
        crop_x: 가로 영상 크롭 중심 0~1.
        pad: 시작/종료 여유 시간(초).

    Output JSON::

        {
          "clip_path": "/path/to/clip_1.mp4",
          "clip_json": "/path/to/clip_1.json",
          "captions_json": "/path/to/captions_1.json",
          "duration_sec": 34.5
        }
    """
    wd = Path(work_dir)
    moments_path = wd / "moments.json"
    detection = MomentDetectionResult.from_dict(
        json.loads(moments_path.read_text())
    )

    top_moments = list(detection.top(len(detection.moments)))
    n = moment_idx + 1  # 1-based filenames

    if moment_idx < 0 or moment_idx >= len(top_moments):
        raise IndexError(
            f"moment_idx={moment_idx} 는 범위 밖입니다 (총 {len(top_moments)}개)"
        )

    moment = top_moments[moment_idx]
    _progress(
        f"✂️  모먼트 [{n}] | {moment.start_sec:.0f}s~{moment.end_sec:.0f}s"
        f" | {moment.hook_question}"
    )

    # 원본 영상 탐색 (scene_*.mp4 제외)
    mp4_candidates = sorted(
        (p for p in wd.glob("*.mp4") if not p.name.startswith("scene_")),
        key=lambda p: p.stat().st_mtime,
    )
    if not mp4_candidates:
        raise FileNotFoundError(f"원본 영상(.mp4) 없음: {wd}")

    source_video = mp4_candidates[-1]
    output_path = wd / f"clip_{n}.mp4"

    _progress(f"✂️  클립 컷: {source_video.name} → {output_path.name}")
    clip_result = make_moment_clip(
        source_video=source_video,
        moment=moment,
        output_path=output_path,
        pad_before=pad,
        pad_after=pad,
        crop_x=crop_x,
    )

    clip_json_path = clip_result.save(wd, n)
    _progress(f"📹 클립 저장: {output_path} ({clip_result.duration_sec:.1f}초)")

    _progress("💬 자막 큐 생성 중...")
    try:
        cues = build_caption_cues(
            work_dir=wd,
            source_url=detection.source_url,
            video_path=source_video,
            moment=moment,
            pad_before=pad,
        )
    except Exception as exc:
        _progress(f"⚠️  자막 큐 생성 실패 (무시): {exc}")
        cues = []

    captions_path = save_caption_cues(cues, wd, n)
    _progress(f"💬 자막 큐 저장: {captions_path} ({len(cues)}개)")

    _emit({
        "clip_path": str(output_path),
        "clip_json": str(clip_json_path),
        "captions_json": str(captions_path),
        "duration_sec": clip_result.duration_sec,
    })


# ── Phase 3: render ───────────────────────────────────────────────────────────

def api_render(work_dir: str, moment_idx: int) -> None:
    """Remotion V3 렌더 → stdout 마지막 줄에 JSON 출력.

    Args:
        work_dir: cut 단계에서 생성된 작업 디렉터리 경로.
        moment_idx: 0-based 인덱스.

    Output JSON::

        {
          "output_path": "/path/to/output_1.mp4"
        }
    """
    wd = Path(work_dir)
    n = moment_idx + 1  # 1-based filenames

    clip_json = wd / f"clip_{n}.json"
    if not clip_json.exists():
        raise FileNotFoundError(
            f"clip_{n}.json 없음. 먼저 cut 실행: api_cut(work_dir, {moment_idx})"
        )

    clip_result = ClipResult.from_dict(json.loads(clip_json.read_text()))

    # 자막 큐 로드 (없으면 빈 리스트)
    captions_json = wd / f"captions_{n}.json"
    captions: list[CaptionCue] = []
    if captions_json.exists():
        raw = json.loads(captions_json.read_text())
        captions = [CaptionCue.from_dict(c) for c in raw]
        _progress(f"💬 자막 큐 {len(captions)}개 로드")
    else:
        _progress("💬 자막 큐 없음 — 자막 없이 렌더")

    # 채널명 + 날짜
    channel = ""
    source_date = datetime.now().strftime("%Y.%m.%d")
    moments_json = wd / "moments.json"
    if moments_json.exists():
        meta = json.loads(moments_json.read_text())
        channel = meta.get("channel", "")
        parts = wd.name.split("_")
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
            raw_d = parts[0]
            source_date = f"{raw_d[:4]}.{raw_d[4:6]}.{raw_d[6:8]}"

    output_path = wd / f"output_{n}.mp4"
    _progress(f"🎬 렌더 시작: {output_path.name}")

    result_path = render_moment_short(
        clip_result=clip_result,
        captions=captions,
        channel=channel,
        source_date=source_date,
        output_path=output_path,
    )

    _progress("⚠️  업로드 전 검수 필수 (자동 업로드 차단)")
    _emit({"output_path": str(result_path)})


# ── Phase 4: meta ─────────────────────────────────────────────────────────────

def api_meta(work_dir: str, moment_idx: int) -> None:
    """제목 후보 + 해시태그 + 고정댓글 생성 → stdout 마지막 줄에 JSON 출력.

    Args:
        work_dir: detect 단계에서 생성된 작업 디렉터리 경로.
        moment_idx: 0-based 인덱스.

    Output JSON::

        {
          "title_candidates": ["제목1?", "제목2?", "제목3?"],
          "hashtags": ["#정치", "#국회", "#쇼츠"],
          "pinned_comment": "여러분이라면...?"
        }
    """
    wd = Path(work_dir)
    moments_path = wd / "moments.json"
    detection = MomentDetectionResult.from_dict(
        json.loads(moments_path.read_text())
    )

    top_moments = list(detection.top(len(detection.moments)))
    if moment_idx < 0 or moment_idx >= len(top_moments):
        raise IndexError(
            f"moment_idx={moment_idx} 는 범위 밖입니다 (총 {len(top_moments)}개)"
        )

    moment = top_moments[moment_idx]
    _progress(f"✍️  메타데이터 생성 중 (모먼트 [{moment_idx + 1}])...")

    meta_result = generate_meta(
        video_title=detection.video_title,
        channel=detection.channel,
        moment_hook=moment.hook_question,
        moment_summary=moment.summary,
        moment_kind=moment.kind,
    )

    _emit(meta_result.to_dict())


# ── CLI 진입점 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(
        prog="python3 -m src.jpolitics.api_bridge",
        description="정치쇼츠 V3 Next.js API 브릿지",
    )
    p.add_argument("command", choices=["detect", "cut", "render", "meta"])
    p.add_argument("--url")
    p.add_argument("--work-dir")
    p.add_argument("--moment-idx", type=int, default=0)
    p.add_argument("--crop-x", type=float, default=0.5)
    p.add_argument("--pad", type=float, default=0.5)
    p.add_argument("--no-multimodal", action="store_true")
    args = p.parse_args()

    if args.command == "detect":
        if not args.url:
            p.error("detect 명령에는 --url 이 필요합니다")
        api_detect(args.url, args.no_multimodal)
    elif args.command == "cut":
        if not args.work_dir:
            p.error("cut 명령에는 --work-dir 이 필요합니다")
        api_cut(args.work_dir, args.moment_idx, args.crop_x, args.pad)
    elif args.command == "render":
        if not args.work_dir:
            p.error("render 명령에는 --work-dir 이 필요합니다")
        api_render(args.work_dir, args.moment_idx)
    elif args.command == "meta":
        if not args.work_dir:
            p.error("meta 명령에는 --work-dir 이 필요합니다")
        api_meta(args.work_dir, args.moment_idx)
