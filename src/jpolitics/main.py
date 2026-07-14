"""정치쇼츠 V3 CLI — 모먼트 직캠 (Feature 027).

Usage:
    python3 -m src.jpolitics.main detect <YouTube URL> [--top 5] [--no-multimodal]
    python3 -m src.jpolitics.main cut <work_dir> --moment 1 [--crop-x 0.5] [--pad 0.5]
    python3 -m src.jpolitics.main render <work_dir> --moment 1
    python3 -m src.jpolitics.main run <URL> [--moment auto] [--no-multimodal]

Phase 1: 모먼트 검출.
Phase 2: 클립 컷 + 자막 큐 생성.
Phase 3: Remotion 렌더 → 최종 MP4.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from src.jpolitics.constants import DEFAULT_TOP_N, JPOLITICS_DATA_DIR
from src.jpolitics.logger import logger

_KIND_LABEL = {
    "laughter": "😂 웃음",
    "clash": "⚔️ 충돌",
    "outburst": "📢 언성",
    "gaffe": "🫢 실언",
    "silence": "🤐 정적",
    "other": "✨ 기타",
}


def _slugify(title: str, max_len: int = 24) -> str:
    slug = re.sub(r"[^\w가-힣]+", "_", title).strip("_")
    return slug[:max_len] or "video"


def cmd_detect(args: argparse.Namespace) -> int:
    # Read-only imports (격리 boundary — V2 모듈 편집 금지)
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
    from src.jpolitics.models.moment import MomentDetectionResult

    url = args.url
    print(f"📥 영상 메타데이터 조회: {url}", file=sys.stderr)
    try:
        meta = get_video_metadata(url)
    except Exception as e:
        print(f"❌ 메타데이터 조회 실패: {e}", file=sys.stderr)
        return 1

    title = meta.get("title") or "untitled"
    channel = meta.get("channel") or meta.get("uploader") or ""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = JPOLITICS_DATA_DIR / f"{ts}_{_slugify(title)}"
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 영상 다운로드 중... ({title})", file=sys.stderr)
    try:
        video_path = download_video(url, work_dir)
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}", file=sys.stderr)
        return 2

    moments = []
    detector = ""
    if not args.no_multimodal:
        print("🔍 Gemini 멀티모달 모먼트 검출 중 (표정·웃음·정적 포함)...", file=sys.stderr)
        try:
            moments = detect_moments_from_video(video_path)
            detector = "gemini_multimodal"
        except MomentDetectError as e:
            logger.warning("멀티모달 검출 실패 — transcript 폴백: %s", e)

    if not moments:
        print("🔍 transcript 기반 모먼트 검출 중 (폴백)...", file=sys.stderr)
        try:
            segments = transcribe_video_or_fallback(url=url, video_path=video_path, out_dir=work_dir)
        except TranscriptUnavailableError as e:
            print(f"❌ transcript 확보 실패: {e}", file=sys.stderr)
            return 3
        try:
            moments = detect_moments_from_transcript(segments)
            detector = "transcript"
        except MomentDetectError as e:
            print(f"❌ 모먼트 검출 실패: {e}", file=sys.stderr)
            return 4

    result = MomentDetectionResult(
        source_url=url,
        video_title=title,
        channel=channel,
        detector=detector,
        moments=tuple(moments),
    )
    out_path = result.save(work_dir / "moments.json")

    top = result.top(args.top)
    print(f"\n✅ 모먼트 {len(result.moments)}개 검출 (검출기: {detector}) — 상위 {len(top)}개:")
    for i, m in enumerate(top, 1):
        label = _KIND_LABEL.get(m.kind, m.kind)
        print(f"\n  [{i}] {label} | {m.start_sec:.0f}s~{m.end_sec:.0f}s ({m.duration_sec:.0f}초) | 확신도 {m.confidence:.0%}")
        print(f"      훅: {m.hook_question}")
        print(f"      내용: {m.summary}")
        if m.speaker:
            print(f"      화자: {m.speaker}")
    print(f"\n📁 저장: {out_path}")
    print(f"다음 단계(Phase 2): python3 -m src.jpolitics.main cut {work_dir} --moment 1")
    return 0


def cmd_cut(args: argparse.Namespace) -> int:
    """Phase 2: work_dir 의 moments.json 에서 모먼트 선택 → 클립 컷 + 자막 큐."""
    import json

    from src.jpolitics.models.moment import MomentDetectionResult
    from src.jpolitics.video.clip_maker import ClipMakeError, make_moment_clip
    from src.jpolitics.video.captions import build_caption_cues, save_caption_cues

    work_dir = Path(args.work_dir)
    moments_path = work_dir / "moments.json"
    if not moments_path.exists():
        print(f"❌ moments.json 없음: {moments_path}", file=sys.stderr)
        return 1

    detection = MomentDetectionResult.from_dict(json.loads(moments_path.read_text()))
    top_moments = list(detection.top(len(detection.moments)))
    n = args.moment  # 1-based index

    if n < 1 or n > len(top_moments):
        print(
            f"❌ --moment {n} 은 범위 밖입니다 (총 {len(top_moments)}개).",
            file=sys.stderr,
        )
        return 2

    moment = top_moments[n - 1]
    label = _KIND_LABEL.get(moment.kind, moment.kind)
    print(
        f"✂️  모먼트 [{n}] {label} | {moment.start_sec:.0f}s~{moment.end_sec:.0f}s "
        f"| {moment.hook_question}",
        file=sys.stderr,
    )

    # 원본 영상 자동 탐색 (scene_*.mp4 제외)
    mp4_candidates = sorted(
        (p for p in work_dir.glob("*.mp4") if not p.name.startswith("scene_")),
        key=lambda p: p.stat().st_mtime,
    )
    if not mp4_candidates:
        print(f"❌ 원본 영상(.mp4)을 work_dir에서 찾을 수 없습니다: {work_dir}", file=sys.stderr)
        return 3

    source_video = mp4_candidates[-1]
    output_path = work_dir / f"clip_{n}.mp4"
    pad = args.pad

    print(f"✂️  클립 컷 중: {source_video.name} → {output_path.name}", file=sys.stderr)
    try:
        clip_result = make_moment_clip(
            source_video=source_video,
            moment=moment,
            output_path=output_path,
            pad_before=pad,
            pad_after=pad,
            crop_x=args.crop_x,
        )
    except ClipMakeError as e:
        print(f"❌ 클립 생성 실패: {e}", file=sys.stderr)
        return 4

    json_path = clip_result.save(work_dir, n)
    print(f"📹 클립 저장: {output_path} ({clip_result.duration_sec:.1f}초)", file=sys.stderr)

    # 자막 큐 생성
    print("💬 자막 큐 생성 중...", file=sys.stderr)
    try:
        cues = build_caption_cues(
            work_dir=work_dir,
            source_url=detection.source_url,
            video_path=source_video,
            moment=moment,
            pad_before=pad,
        )
    except Exception as e:
        logger.warning("자막 큐 생성 실패 (무시하고 계속): %s", e)
        cues = []

    captions_path = save_caption_cues(cues, work_dir, n)
    print(f"💬 자막 큐 저장: {captions_path} ({len(cues)}개)", file=sys.stderr)

    print(f"\n✅ 완료!")
    print(f"   클립:  {output_path}")
    print(f"   메타:  {json_path}")
    print(f"   자막:  {captions_path}")
    print(f"\n다음 단계(Phase 3): python3 -m src.jpolitics.main render {work_dir} --moment {n}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Phase 3: 클립 + 자막 큐 → Remotion 렌더 → MP4."""
    import json

    from src.jpolitics.models.clip import CaptionCue, ClipResult
    from src.jpolitics.models.moment import MomentDetectionResult
    from src.jpolitics.video.renderer import RenderError, render_moment_short

    work_dir = Path(args.work_dir)
    n = args.moment

    clip_json = work_dir / f"clip_{n}.json"
    if not clip_json.exists():
        print(f"❌ clip_{n}.json 없음. 먼저 cut 실행: python3 -m src.jpolitics.main cut {work_dir} --moment {n}", file=sys.stderr)
        return 1

    clip_result = ClipResult.from_dict(json.loads(clip_json.read_text()))

    # 자막 큐 로드 (없으면 빈 리스트)
    captions_json = work_dir / f"captions_{n}.json"
    captions: list[CaptionCue] = []
    if captions_json.exists():
        raw = json.loads(captions_json.read_text())
        captions = [CaptionCue.from_dict(c) for c in raw]
        print(f"💬 자막 큐 {len(captions)}개 로드", file=sys.stderr)
    else:
        print("💬 자막 큐 없음 — 자막 없이 렌더", file=sys.stderr)

    # 채널명 + 날짜 — moments.json 에서
    channel = ""
    source_date = datetime.now().strftime("%Y.%m.%d")
    moments_json = work_dir / "moments.json"
    if moments_json.exists():
        meta = json.loads(moments_json.read_text())
        channel = meta.get("channel", "")
        # 날짜는 work_dir 이름에서 ts prefix 추출 (YYYYMMDD_HHMMSS_slug)
        parts = work_dir.name.split("_")
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
            raw_d = parts[0]
            source_date = f"{raw_d[:4]}.{raw_d[4:6]}.{raw_d[6:8]}"

    output_path = work_dir / f"output_{n}.mp4"
    print(f"🎬 렌더 시작: {output_path.name}", file=sys.stderr)

    try:
        result_path = render_moment_short(
            clip_result=clip_result,
            captions=captions,
            channel=channel,
            source_date=source_date,
            output_path=output_path,
        )
    except RenderError as e:
        print(f"❌ 렌더 실패: {e}", file=sys.stderr)
        return 2

    print(f"\n✅ 렌더 완료!")
    print(f"   출력: {result_path}")
    print("   ⚠️  업로드 전 검수 필수 (자동 업로드 차단)")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """detect → cut → render 일괄 실행."""
    # 1단계: detect
    detect_ns = argparse.Namespace(
        url=args.url,
        top=DEFAULT_TOP_N,
        no_multimodal=args.no_multimodal,
    )
    ret = cmd_detect(detect_ns)
    if ret != 0:
        return ret

    # detect가 만든 가장 최신 work_dir 탐색
    candidates = sorted(JPOLITICS_DATA_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("❌ work_dir 탐색 실패", file=sys.stderr)
        return 5

    work_dir = candidates[0]

    # 모먼트 순위 결정
    import json
    moments_json = work_dir / "moments.json"
    n = 1
    if args.moment != "auto":
        n = int(args.moment)

    # 2단계: cut
    cut_ns = argparse.Namespace(
        work_dir=str(work_dir),
        moment=n,
        crop_x=0.5,
        pad=0.5,
    )
    ret = cmd_cut(cut_ns)
    if ret != 0:
        return ret

    # 3단계: render
    render_ns = argparse.Namespace(work_dir=str(work_dir), moment=n)
    return cmd_render(render_ns)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.jpolitics.main",
        description="정치쇼츠 V3 — 모먼트 직캠",
    )
    sub = parser.add_subparsers(dest="command")

    detect = sub.add_parser("detect", help="YouTube 영상에서 감정 모먼트 검출")
    detect.add_argument("url", help="YouTube URL")
    detect.add_argument("--top", type=int, default=DEFAULT_TOP_N, help="출력할 상위 후보 수")
    detect.add_argument(
        "--no-multimodal", action="store_true",
        help="Gemini 멀티모달 생략, transcript 폴백만 사용 (무료 한도 절약)",
    )

    cut = sub.add_parser("cut", help="모먼트를 9:16 클립으로 컷 + 자막 큐 생성 (Phase 2)")
    cut.add_argument("work_dir", help="detect 단계에서 생성된 작업 디렉터리")
    cut.add_argument("--moment", type=int, default=1, metavar="N", help="사용할 모먼트 순위 (기본 1)")
    cut.add_argument("--crop-x", type=float, default=0.5, dest="crop_x",
                     metavar="0~1", help="가로 영상 크롭 중심 (기본 0.5)")
    cut.add_argument("--pad", type=float, default=0.5,
                     metavar="SEC", help="시작/종료 여유 시간(초) (기본 0.5)")

    render = sub.add_parser("render", help="클립 + 자막 큐 → Remotion 렌더 → MP4 (Phase 3)")
    render.add_argument("work_dir", help="cut 단계에서 생성된 작업 디렉터리")
    render.add_argument("--moment", type=int, default=1, metavar="N", help="렌더할 모먼트 순위 (기본 1)")

    run_p = sub.add_parser("run", help="detect→cut→render 일괄 실행")
    run_p.add_argument("url", help="YouTube URL")
    run_p.add_argument("--moment", default="auto", metavar="N|auto",
                       help="사용할 모먼트 순위 (기본 auto=확신도 1위)")
    run_p.add_argument("--no-multimodal", action="store_true",
                       help="Gemini 멀티모달 생략")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "detect":
        return cmd_detect(args)
    if args.command == "cut":
        return cmd_cut(args)
    if args.command == "render":
        return cmd_render(args)
    if args.command == "run":
        return cmd_run(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
