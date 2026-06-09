"""T024 [US1]: V3 CLI entry — python3 -m src.jpolitics.main.

흐름:
1. transcript 추출 (yt-dlp 또는 사용자 제공)
2. generate_three_plans (Stage A Gemini + Stage B Claude × 3)
3. 사용자 선택 (--select-plan 또는 인터랙티브)
4. plan_to_script (인물 카드 페치 + 클립 cut)
5. TTS 합성 (락인 InJoonNeural +22%, gap 300 ms)
6. Remotion V3 렌더 → MP4
7. 3줄 요약 + 해시태그 생성

격리: src.main 무관, 독립 entry.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.jpolitics.analyzer.planner import (
    _slugify,
    generate_three_plans,
    plan_to_script,
)
from src.jpolitics.constants import JPOLITICS_OUTPUT_DIR
from src.jpolitics.logger import get_logger
from src.jpolitics.models.plan import JpoliticsPlan
from src.jpolitics.models.script import JpoliticsScript
from src.jpolitics.tts.voice import SceneTiming, synthesize
from src.jpolitics.video.renderer import render

logger = get_logger("main")


# Exit codes (contracts/cli.md)
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT_INVALID = 2
EXIT_TRANSCRIPT_FAIL = 3
EXIT_PLANNER_FAIL = 4
EXIT_TTS_FAIL = 5
EXIT_RENDER_FAIL = 6


def _is_youtube_url(url: str) -> bool:
    return bool(
        re.match(
            r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url, re.IGNORECASE
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m src.jpolitics.main",
        description="정치쇼츠 V3 — @김정치입니다 격리 모드 (jpolitics)",
    )
    parser.add_argument(
        "youtube_url",
        nargs="?",
        default=None,
        help="YouTube 영상 URL (--source-type youtube 모드)",
    )
    parser.add_argument(
        "--source-type",
        choices=["youtube", "topic"],
        default="youtube",
        help="입력 모드 (기본: youtube)",
    )
    parser.add_argument("--topic", default=None, help="주제 텍스트 (topic 모드)")
    parser.add_argument("--tone", default="분노·격앙", help="톤 (topic 모드)")
    parser.add_argument("--details", default="", help="상세 설명 (topic 모드)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="출력 디렉토리 (기본: data/jpolitics/{ts}_{slug}/)",
    )
    parser.add_argument(
        "--select-plan",
        type=int,
        choices=[1, 2, 3],
        default=None,
        help="기획안 자동 선택 (1/2/3)",
    )
    parser.add_argument(
        "--plans-only", action="store_true", help="3 plans 생성만 (영상 X)"
    )
    parser.add_argument(
        "--render-only", action="store_true", help="기존 script로 렌더만"
    )
    parser.add_argument(
        "--script-file", type=Path, default=None, help="기존 script.json 경로"
    )
    parser.add_argument(
        "--video-title", default=None, help="영상 제목 명시 (URL/topic 모드 공통)"
    )
    return parser


def validate_args(args: argparse.Namespace) -> int | None:
    """Returns None if OK, else exit code."""
    if args.render_only:
        if not args.script_file or not args.script_file.exists():
            logger.error("--render-only requires existing --script-file")
            return EXIT_INPUT_INVALID
        return None
    if args.source_type == "topic":
        if not args.topic:
            logger.error("--source-type topic requires --topic")
            return EXIT_INPUT_INVALID
    else:  # youtube
        if not args.youtube_url or not _is_youtube_url(args.youtube_url):
            logger.error(
                "youtube_url required and must be a YouTube URL (got: %s)",
                args.youtube_url,
            )
            return EXIT_INPUT_INVALID
    return None


def _select_plan_interactive(plans: list) -> int:
    """사용자 인터랙티브 선택 (CLI prompt)."""
    print("\n기획안 3개 생성 완료:", file=sys.stderr)
    for i, plan in enumerate(plans, 1):
        print(
            f"  {i}. [{plan.angle}] {plan.topic} — {plan.hook}",
            file=sys.stderr,
        )
    while True:
        choice = input("선택 (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        print("1, 2, 3 중 하나를 입력하세요.", file=sys.stderr)


def _generate_summary(script) -> dict[str, Any]:
    """3줄 요약 + 해시태그 (FR-032, 고정 규칙)."""
    title = script.metadata.title
    scenes_text = " / ".join(s.text for s in script.scenes[:3])
    return {
        "lines": [
            f"{title}을(를) 정리한 60초 쇼츠입니다.",
            scenes_text or "주요 발언과 핵심 데이터를 한눈에.",
            "검수 후 본인 책임으로 게시해 주세요.",
        ],
        "hashtags": [
            f"#{title.replace(' ', '')}",
            "#정치쇼츠",
            "#정치",
            "#한국정치",
            "#뉴스",
        ],
    }


def _fetch_youtube_transcript(
    args: argparse.Namespace,
) -> tuple[list[dict], str, float, Path]:
    """YouTube URL → 영상 다운로드 + transcript 추출 (010 FR-002).

    V2 (political_pro)와 동일한 폴백 체인(VTT → Gemini Files → Whisper)을
    V3로 옮긴 헬퍼. plans_only / full pipeline 두 경로에서 공통 사용.

    Returns:
        (transcript_segments, fetched_video_title, video_duration_sec, output_dir)
    """
    import subprocess as _sub

    from src.scraper.youtube_downloader import (
        TranscriptUnavailableError,
        download_video,
        get_video_metadata,
        transcribe_video_or_fallback,
    )

    url = (args.youtube_url or "").strip()
    if not url:
        raise ValueError("youtube_url이 비어 있습니다")

    # output_dir 결정
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug_src = args.video_title or "video"
        slug = re.sub(r"[^\w가-힣]+", "_", slug_src)[:30] or "video"
        out_dir = JPOLITICS_OUTPUT_DIR / f"{ts}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("YouTube 메타데이터 + 다운로드 중: %s", url)
    meta = get_video_metadata(url)
    vp = download_video(url, out_dir)
    fetched_title = (meta.get("title") or "").strip() or vp.stem

    logger.info("Transcript 추출 중 (VTT → Gemini → Whisper 폴백)")
    try:
        transcript = transcribe_video_or_fallback(
            url=url, video_path=vp, out_dir=out_dir
        )
    except TranscriptUnavailableError as e:
        raise RuntimeError(f"Transcript 확보 실패: {e}") from e
    if not transcript:
        raise RuntimeError("유효한 transcript가 비어 있습니다")

    # duration
    probe = _sub.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(vp)],
        capture_output=True, text=True,
    )
    try:
        duration_sec = float(probe.stdout.strip())
    except Exception:
        duration_sec = transcript[-1].get("end", 60.0) if transcript else 60.0

    # transcript.json 저장
    tp = out_dir / "transcript.json"
    tp.write_text(
        json.dumps({"segments": transcript}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return transcript, fetched_title, duration_sec, out_dir


def run(args: argparse.Namespace) -> int:
    err = validate_args(args)
    if err is not None:
        return err

    if args.plans_only:
        # 3 plans만 생성하고 종료
        try:
            if args.source_type == "youtube":
                transcript, fetched_title, duration_sec, ydir = (
                    _fetch_youtube_transcript(args)
                )
                video_title = args.video_title or fetched_title
                output_dir_override: Path | None = ydir
            else:
                video_title = args.video_title or args.topic or "영상"
                transcript = []
                duration_sec = 60.0
                output_dir_override = (
                    Path(args.output_dir) if args.output_dir else None
                )
            result = generate_three_plans(
                youtube_url=args.youtube_url or "",
                video_title=video_title,
                video_duration_sec=duration_sec,
                transcript=transcript,
                output_dir=output_dir_override,
            )
            print(
                json.dumps(
                    {"ok": True, "outputDir": result.output_dir},
                    ensure_ascii=False,
                )
            )
            return EXIT_OK
        except Exception as e:
            logger.exception("plans-only 실행 실패")
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return EXIT_PLANNER_FAIL

    # --render-only: 기존 script.json → TTS + 렌더만
    if args.render_only:
        try:
            return _run_render_only(args)
        except Exception as e:
            logger.exception("--render-only 실행 실패")
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            return EXIT_RENDER_FAIL

    # 전체 파이프라인 (T041/T055/T063/T071 E2E entry):
    # plans 생성 → plan 선택 → script 변환 → TTS → Remotion 렌더 → summary
    try:
        return _run_full_pipeline(args)
    except Exception as e:
        logger.exception("Full pipeline 실행 실패")
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return EXIT_ERROR


def _run_full_pipeline(args: argparse.Namespace) -> int:
    """plans → select → script → TTS → render → summary."""
    if args.source_type == "youtube":
        transcript, fetched_title, duration_sec, ydir = _fetch_youtube_transcript(args)
        video_title = args.video_title or fetched_title
        output_dir_override: Path | None = ydir
    else:
        video_title = args.video_title or args.topic or "영상"
        transcript = []
        duration_sec = 60.0
        output_dir_override = Path(args.output_dir) if args.output_dir else None

    # Step 1: 3 plans 생성 + plans.json + gemini_analysis.json 저장
    logger.info("Step 1/5: 3 plans 생성 (transcript %d segments)", len(transcript))
    three_plans = generate_three_plans(
        youtube_url=args.youtube_url or "",
        video_title=video_title,
        video_duration_sec=duration_sec,
        transcript=transcript,
        output_dir=output_dir_override,
    )
    output_dir = Path(three_plans.output_dir)

    # Step 2: plan 선택
    if args.select_plan is not None:
        selected_rank = args.select_plan
    else:
        selected_rank = _select_plan_interactive(list(three_plans.plans))
    selected_plan = next(
        (p for p in three_plans.plans if p.rank == selected_rank), None
    )
    if selected_plan is None:
        raise RuntimeError(f"선택한 rank={selected_rank} 기획안이 없습니다.")
    logger.info(
        "Step 2/5: plan rank=%d angle=%s topic=%s",
        selected_plan.rank,
        selected_plan.angle,
        selected_plan.topic,
    )

    # Step 3: plan → script 변환 (인물 카드 페치 + 클립 cut)
    logger.info("Step 3/5: plan_to_script (카드 페치 + 클립 cut)")
    script = plan_to_script(selected_plan)
    script_path = output_dir / "script.json"
    script_path.write_text(
        json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Step 4: TTS 합성 + Remotion 렌더
    audio_path = output_dir / "audio.mp3"
    logger.info("Step 4/5: TTS 합성 (InJoonNeural +22%%, gap 300ms)")
    _, scene_timings = synthesize(script, audio_path)

    video_path = output_dir / "video.mp4"
    logger.info("Step 5/5: Remotion V3 렌더 → %s", video_path)
    render(
        script=script,
        audio_path=audio_path,
        scene_timings=scene_timings,
        output_path=video_path,
    )

    # Step 6: summary.txt + 3줄 요약 + 해시태그
    summary = _generate_summary(script)
    summary_path = output_dir / "summary.txt"
    summary_text = "\n".join(summary["lines"]) + "\n\n" + " ".join(summary["hashtags"])
    summary_path.write_text(summary_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "outputDir": str(output_dir),
                "videoPath": str(video_path),
                "audioPath": str(audio_path),
                "scriptPath": str(script_path),
                "summaryPath": str(summary_path),
                "summary": summary,
            },
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def _run_render_only(args: argparse.Namespace) -> int:
    """기존 script.json → TTS + 렌더만 (E2E 디버깅용)."""
    script_data = json.loads(args.script_file.read_text(encoding="utf-8"))
    script = JpoliticsScript.from_dict(script_data)
    output_dir = args.output_dir or args.script_file.parent
    audio_path = output_dir / "audio.mp3"
    _, scene_timings = synthesize(script, audio_path)
    video_path = output_dir / "video.mp4"
    render(
        script=script,
        audio_path=audio_path,
        scene_timings=scene_timings,
        output_path=video_path,
    )
    print(
        json.dumps(
            {"ok": True, "outputDir": str(output_dir), "videoPath": str(video_path)},
            ensure_ascii=False,
        )
    )
    return EXIT_OK


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run(args)
    except SystemExit:
        raise
    except Exception:
        logger.exception("Unhandled error")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
