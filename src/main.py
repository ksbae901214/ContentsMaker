"""ContentsMaker CLI - Blind post to Shorts pipeline.

Usage:
    python3 -m src.main image screenshot1.png [screenshot2.png ...]
    python3 -m src.main manual --file <path>
    python3 -m src.main analyze --file <raw.json> [--with-tts]
    python3 -m src.main tts --file <script.json>
    python3 -m src.main render --script <script.json> --audio <voice.mp3>
    python3 -m src.main pipeline --file <raw.json>
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.scraper.manual_input import (
    ManualInputError,
    collect_interactive,
    load_from_file,
    save_post,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_image(args: argparse.Namespace) -> int:
    """Handle the 'image' subcommand — screenshot to video pipeline."""
    from src.scraper.image_extractor import ImageExtractError, extract_from_images
    from src.scraper.manual_input import save_post
    from src.analyzer.claude_analyzer import AnalyzerError, analyze
    from src.video.renderer import RenderError, render_video

    try:
        image_paths = [Path(p) for p in args.images]
        for p in image_paths:
            if not p.exists():
                print(f"\n❌ 이미지 파일을 찾을 수 없습니다: {p}", file=sys.stderr)
                return 1

        # Step 1: Extract text from images
        print(f"📸 Step 1/4: 이미지에서 텍스트 추출 중... ({len(image_paths)}장)")
        post = extract_from_images(image_paths)
        raw_path = save_post(post)
        print(f"   제목: {post.title}")
        print(f"   본문: {post.body[:50]}...")
        print(f"   댓글: {len(post.comments)}개")
        print(f"   저장: {raw_path}")

        # Step 2: Analyze
        print("📝 Step 2/4: AI 분석 중...")
        script, _ = analyze(post)
        print(f"   감정: {script.metadata.emotion_type} | 씬: {len(script.scenes)}개 | 길이: {script.metadata.duration}초")

        # Step 3: Generate illustrations
        use_refs = not getattr(args, "no_references", False)
        scene_images = _run_illustrations(script, use_references=use_refs)

        # Step 4: TTS
        print("🎙️  Step 4/5: 음성 생성 중...")
        tts_code, voice_path, scene_timings = _run_tts(script)
        if tts_code != 0:
            print("   ⚠️  TTS 실패, 무음 영상으로 계속합니다.")
            voice_path = None
            scene_timings = None

        # Step 5: Render
        print("🎬 Step 5/5: 영상 렌더링 중...")
        use_bgm = not getattr(args, "no_bgm", False)
        output_path = render_video(script, audio_path=voice_path, scene_images=scene_images, use_bgm=use_bgm, scene_timings=scene_timings)
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 완료! 이미지 → 영상 변환 성공")
        print(f"   영상: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        print(f"   감정: {script.metadata.emotion_type}")
        print(f"   길이: {script.metadata.duration}초")
        if scene_images:
            print(f"   만화: {len(scene_images)}장")
        return 0

    except (ImageExtractError, AnalyzerError, RenderError) as e:
        logger.error("오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        return 130


def cmd_manual(args: argparse.Namespace) -> int:
    """Handle the 'manual' subcommand."""
    try:
        if args.file:
            file_path = Path(args.file)
            logger.info("JSON 파일 로딩: %s", file_path)
            post = load_from_file(file_path)
        elif args.interactive:
            post = collect_interactive()
        else:
            logger.error("--file 또는 --interactive 옵션이 필요합니다")
            return 1

        saved_path = save_post(post)
        logger.info("저장 완료: %s", saved_path)
        print(f"\n✅ 저장 완료: {saved_path}")
        print(f"   제목: {post.title}")
        print(f"   본문: {post.body[:50]}...")
        print(f"   댓글: {len(post.comments)}개")
        return 0

    except ManualInputError as e:
        logger.error("입력 오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        return 130


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle the 'analyze' subcommand."""
    from src.analyzer.claude_analyzer import AnalyzerError, analyze
    from src.scraper.models import BlindPost

    try:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"\n❌ 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
            return 1

        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))
        post = BlindPost.from_dict(data)

        logger.info("분석 시작: %s", post.title)
        script, _ = analyze(post)

        print(f"\n✅ 스크립트 생성 완료")
        print(f"   제목: {script.metadata.title}")
        print(f"   감정: {script.metadata.emotion_type}")
        print(f"   씬 수: {len(script.scenes)}")
        print(f"   길이: {script.metadata.duration}초")

        if args.with_tts:
            code, _, _ = _run_tts(script)
            return code

        return 0

    except AnalyzerError as e:
        logger.error("분석 오류: %s", e)
        print(f"\n❌ 분석 오류: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("예상치 못한 오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1


def cmd_tts(args: argparse.Namespace) -> int:
    """Handle the 'tts' subcommand."""
    from src.analyzer.script_models import ShortsScript

    try:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"\n❌ 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
            return 1

        script = ShortsScript.load(file_path)
        provider = getattr(args, "provider", "edge")
        voice = getattr(args, "voice", None)
        code, _, _ = _run_tts(script, provider=provider, voice=voice)
        return code

    except Exception as e:
        logger.error("TTS 오류: %s", e)
        print(f"\n❌ TTS 오류: {e}", file=sys.stderr)
        return 1


def _run_tts(script, provider: str = "gemini", voice: str | None = None):
    """Run TTS generation with per-scene timing.

    Args:
        script: ShortsScript instance.
        provider: "gemini" (Google AI Studio, default) or "edge" (Microsoft).
        voice: Gemini voice name (e.g. "Leda"); ignored when provider="edge".

    Returns (exit_code, voice_path, scene_timings).
    scene_timings is a list of {scene_id, start_ms, end_ms} dicts.
    On Gemini failure (no API key, quota, network), automatically falls back to edge-tts.
    """
    if provider == "gemini":
        from src.tts.gemini_tts_generator import (
            DEFAULT_VOICE,
            GeminiTTSError,
            generate_voice_with_timing_gemini,
        )
        try:
            logger.info("Gemini TTS 생성 시작 (voice=%s)...", voice or DEFAULT_VOICE)
            voice_path, scene_timings = generate_voice_with_timing_gemini(
                script, voice_name=voice or DEFAULT_VOICE,
            )
            file_size_kb = voice_path.stat().st_size / 1024
            print(f"\n✅ Gemini 음성 생성 완료")
            print(f"   파일: {voice_path}")
            print(f"   크기: {file_size_kb:.1f} KB")
            print(f"   보이스: {voice or DEFAULT_VOICE}")
            return 0, voice_path, scene_timings
        except GeminiTTSError as e:
            logger.warning("Gemini TTS 실패, edge-tts로 폴백: %s", e)
            print(f"\n⚠️  Gemini TTS 실패 → edge-tts 폴백: {e}", file=sys.stderr)
            # fall through to edge-tts below

    from src.tts.edge_tts_generator import TTSError, generate_voice_with_timing

    try:
        logger.info("TTS 생성 시작...")
        voice_path, scene_timings = generate_voice_with_timing(script)
        file_size_kb = voice_path.stat().st_size / 1024

        print(f"\n✅ 음성 생성 완료")
        print(f"   파일: {voice_path}")
        print(f"   크기: {file_size_kb:.1f} KB")
        print(f"   음성: {script.audio.voice}")
        return 0, voice_path, scene_timings

    except TTSError as e:
        logger.error("TTS 오류: %s", e)
        print(f"\n❌ TTS 오류: {e}", file=sys.stderr)
        return 1, None, None


def _run_illustrations(script, use_references: bool = True) -> list[dict] | None:
    """Generate manga illustrations for scenes. Returns None if unavailable."""
    import os
    from src.config.settings import DEFAULT_IMAGE_PROVIDER

    provider = DEFAULT_IMAGE_PROVIDER  # "freepik" or "gpt"

    if provider == "gpt" and not os.environ.get("OPENAI_API_KEY"):
        print("🎨 Step 3/5: 만화 이미지 생성 스킵 (OPENAI_API_KEY 미설정)")
        print("   그라데이션 배경으로 대체합니다.")
        return None

    from src.illustrator.image_generator import ImageGenerateError, generate_scene_images
    from src.illustrator.reference_manager import is_available as refs_available, get_all_references
    try:
        has_refs = use_references and refs_available() and provider == "gpt"
        provider_label = "Freepik (무제한)" if provider == "freepik" else "GPT Image API"
        if has_refs:
            ref_count = len(get_all_references())
            print(f"🎨 Step 3/5: 만화 이미지 생성 중 ({len(script.scenes)}씬, 레퍼런스 {ref_count}장, {provider_label})...")
        else:
            print(f"🎨 Step 3/5: 만화 이미지 생성 중 ({len(script.scenes)}씬, {provider_label})...")
        results = generate_scene_images(script, use_references=use_references, provider=provider)
        cost_str = f"${len(results) * 0.005:.3f}" if provider == "gpt" else "$0.000 (Premium+)"
        print(f"   생성: {len(results)}장 ({cost_str})")
        return results
    except ImageGenerateError as e:
        logger.warning("이미지 생성 실패, 그라데이션으로 대체: %s", e)
        print(f"   ⚠️  이미지 생성 실패: {e}")
        print("   그라데이션 배경으로 대체합니다.")
        return None


def cmd_render(args: argparse.Namespace) -> int:
    """Handle the 'render' subcommand."""
    from src.analyzer.script_models import ShortsScript
    from src.video.renderer import RenderError, render_video

    try:
        script_path = Path(args.script)
        if not script_path.exists():
            print(f"\n❌ 스크립트 파일을 찾을 수 없습니다: {script_path}", file=sys.stderr)
            return 1

        script = ShortsScript.load(script_path)

        audio_path = Path(args.audio) if args.audio else None
        if audio_path and not audio_path.exists():
            print(f"\n❌ 오디오 파일을 찾을 수 없습니다: {audio_path}", file=sys.stderr)
            return 1

        logger.info("렌더링 시작: %s", script.metadata.title)
        output_path = render_video(script, audio_path=audio_path)
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 영상 렌더링 완료")
        print(f"   파일: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        print(f"   감정: {script.metadata.emotion_type}")
        print(f"   길이: {script.metadata.duration}초")
        return 0

    except RenderError as e:
        logger.error("렌더링 오류: %s", e)
        print(f"\n❌ 렌더링 오류: {e}", file=sys.stderr)
        return 1


def cmd_url(args: argparse.Namespace) -> int:
    """Handle the 'url' subcommand — URL to video pipeline."""
    from src.scraper.url_scraper import UrlScrapeError, extract_from_url
    from src.scraper.manual_input import save_post
    from src.analyzer.claude_analyzer import AnalyzerError, analyze
    from src.video.renderer import RenderError, render_video

    try:
        # Step 1: Extract from URL
        print(f"🔗 Step 1/5: URL에서 콘텐츠 추출 중...")
        post = extract_from_url(args.url)
        raw_path = save_post(post)
        print(f"   제목: {post.title}")
        print(f"   본문: {post.body[:50]}...")
        print(f"   댓글: {len(post.comments)}개")

        # Step 2: Analyze
        print("📝 Step 2/5: AI 분석 중...")
        script, _ = analyze(post)
        print(f"   감정: {script.metadata.emotion_type} | 씬: {len(script.scenes)}개")

        # Step 3: Illustrations
        use_refs = not getattr(args, "no_references", False)
        scene_images = _run_illustrations(script, use_references=use_refs)

        # Step 4: TTS
        print("🎙️  Step 4/5: 음성 생성 중...")
        tts_code, voice_path, scene_timings = _run_tts(script)
        if tts_code != 0:
            voice_path = None
            scene_timings = None

        # Step 5: Render
        print("🎬 Step 5/5: 영상 렌더링 중...")
        use_bgm = not getattr(args, "no_bgm", False)
        output_path = render_video(script, audio_path=voice_path, scene_images=scene_images, use_bgm=use_bgm, scene_timings=scene_timings)
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 완료! URL → 영상 변환 성공")
        print(f"   영상: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        return 0

    except (UrlScrapeError, AnalyzerError, RenderError) as e:
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        return 130


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Handle the 'pipeline' subcommand — full raw → video pipeline."""
    from src.analyzer.claude_analyzer import AnalyzerError, analyze
    from src.scraper.models import BlindPost
    from src.video.renderer import RenderError, render_video

    try:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"\n❌ 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
            return 1

        import json
        data = json.loads(file_path.read_text(encoding="utf-8"))
        post = BlindPost.from_dict(data)

        # Step 1: Analyze
        print("📝 Step 1/4: AI 분석 중...")
        script, _ = analyze(post)
        print(f"   감정: {script.metadata.emotion_type} | 씬: {len(script.scenes)}개 | 길이: {script.metadata.duration}초")

        # Step 2: Illustrations
        use_refs = not getattr(args, "no_references", False)
        scene_images = _run_illustrations(script, use_references=use_refs)

        # Step 3: TTS
        print("🎙️  Step 3/4: 음성 생성 중...")
        tts_code, voice_path, scene_timings = _run_tts(script)
        if tts_code != 0:
            print("⚠️  TTS 실패, 무음 영상으로 계속합니다.")
            voice_path = None
            scene_timings = None

        # Step 4: Render
        print("🎬 Step 4/4: 영상 렌더링 중...")
        use_bgm = not getattr(args, "no_bgm", False)
        output_path = render_video(script, audio_path=voice_path, scene_images=scene_images, use_bgm=use_bgm, scene_timings=scene_timings)
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 파이프라인 완료!")
        print(f"   영상: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        if scene_images:
            print(f"   만화: {len(scene_images)}장")
        return 0

    except (AnalyzerError, RenderError) as e:
        logger.error("파이프라인 오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1


def cmd_political_pro(args: argparse.Namespace) -> int:
    """Handle the 'political-pro' subcommand (Feature 009).

    YouTube URL → download + transcript → 3 ShortsPlan (Claude single-call)
    → user picks 1 → plan_to_script → render 9:16 MP4 (original clip + Gemini
    TTS Charon).

    Exit codes:
        0 = success
        2 = invalid input
        3 = youtube download failed
        4 = transcript unavailable
        5 = Claude plan generation failed
        6 = TTS failed
        7 = render failed
    """
    import json as _json
    import subprocess as _sub
    from datetime import datetime

    from src.analyzer.political_planner import (
        PoliticalPlannerError,
        generate_three_plans,
        generate_three_plans_from_topic,
        plan_to_script,
    )
    from src.config.settings import DATA_DIR
    from src.scraper.youtube_downloader import (
        TranscriptUnavailableError,
        download_video,
        get_video_metadata,
        transcribe_video_or_fallback,
    )

    source_type = getattr(args, "source_type", "youtube")

    # Feature 023: topic 모드 분기 — YouTube 다운로드 + transcript 단계 스킵.
    if source_type == "topic":
        topic_text = (getattr(args, "topic", "") or "").strip()
        if not topic_text:
            print("❌ --source-type topic 사용 시 --topic 인자 필수", file=sys.stderr)
            return 2

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = DATA_DIR / "political_pro" / f"{ts}_cli_topic"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"🤔 3개 기획안 생성 중 (topic 모드, Hybrid: Gemini + Claude)...",
              file=sys.stderr)
        try:
            result = generate_three_plans_from_topic(
                topic=topic_text,
                tone=getattr(args, "tone", "분노·격앙"),
                details=getattr(args, "details", "") or "",
                output_dir=out_dir,
            )
        except PoliticalPlannerError as e:
            print(f"❌ topic 기획안 생성 실패: {e}", file=sys.stderr)
            return 5

        if args.plans_only:
            print(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0

        # topic 모드: 영상 다운로드·cut은 web UI 흐름에서 처리. CLI는 기획안 출력까지만.
        # (CLI에서 영상까지 만들고 싶다면 별도 작업 필요 — 추후 확장)
        print("\n💡 topic 모드 CLI는 기획안 출력까지만 지원. "
              "영상 생성은 웹 UI에서 진행하세요.", file=sys.stderr)
        print(_json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    url = args.youtube_url.strip()
    if not url.startswith(("https://", "http://")):
        print("❌ 유효한 URL이 아닙니다 (source-type=youtube)", file=sys.stderr)
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = DATA_DIR / "political_pro" / f"{ts}_cli"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎬 영상 메타데이터 + 다운로드 중... ({url})", file=sys.stderr)
    meta = get_video_metadata(url)
    try:
        vp = download_video(url, out_dir)
    except Exception as e:
        print(f"❌ YouTube 다운로드 실패: {e}", file=sys.stderr)
        return 3
    yt_title = (meta.get("title") or "").strip() or vp.stem
    yt_channel = (meta.get("channel") or "").strip()

    print(f"🎙️ Transcript 확보 중...", file=sys.stderr)
    try:
        transcript = transcribe_video_or_fallback(url=url, video_path=vp, out_dir=out_dir)
    except TranscriptUnavailableError as e:
        print(f"❌ Transcript 확보 실패: {e}", file=sys.stderr)
        return 4
    if not transcript:
        print("❌ 유효한 transcript가 비어 있습니다", file=sys.stderr)
        return 4

    probe = _sub.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(vp)],
        capture_output=True, text=True,
    )
    try:
        duration_sec = float(probe.stdout.strip())
    except Exception:
        duration_sec = transcript[-1]["end"] if transcript else 0.0

    tp = out_dir / "transcript.json"
    tp.write_text(
        _json.dumps({"segments": transcript}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"🤔 3개 기획안 생성 중 (Hybrid: Gemini + Claude)...", file=sys.stderr)
    try:
        result = generate_three_plans(
            youtube_url=url,
            transcript=transcript,
            video_title=yt_title,
            video_duration_sec=duration_sec,
            video_path=str(vp),
            transcript_path=str(tp),
            output_dir=out_dir,
            video_channel=yt_channel,
        )
    except PoliticalPlannerError as e:
        print(f"❌ 기획안 생성 실패: {e}", file=sys.stderr)
        return 5

    if args.plans_only:
        print(_json.dumps(result.to_dict(), ensure_ascii=False))
        return 0

    # Print plan summary to stderr (so plans-only stdout JSON stays clean)
    print("\n────────────────────────────────────────", file=sys.stderr)
    for i, p in enumerate(result.plans):
        print(
            f"[Plan {i + 1}] angle={p.angle}\n"
            f"  주제: {p.topic}\n"
            f"  Hook: \"{p.hook}\"\n"
            f"  구간: {int(p.clip_start_sec // 60):02d}:{int(p.clip_start_sec % 60):02d} "
            f"~ {int(p.clip_end_sec // 60):02d}:{int(p.clip_end_sec % 60):02d}\n"
            f"  CTA: {p.cta}\n",
            file=sys.stderr,
        )
    print("────────────────────────────────────────", file=sys.stderr)

    # Select plan
    if args.interactive:
        try:
            sel = int(input("어떤 기획안으로 영상을 만들까요? (1/2/3): ").strip())
        except (ValueError, EOFError):
            print("❌ 잘못된 입력", file=sys.stderr)
            return 2
        plan_idx = sel - 1
    elif args.plan_idx is not None:
        plan_idx = args.plan_idx
    else:
        print("❌ --plan-idx 또는 --interactive 필요", file=sys.stderr)
        return 2

    if plan_idx not in (0, 1, 2):
        print(f"❌ plan-idx 0/1/2 범위 외 ({plan_idx})", file=sys.stderr)
        return 2

    plan = result.plans[plan_idx]
    print(f"✅ Plan {plan_idx + 1} 선택됨 — {plan.topic}", file=sys.stderr)

    script = plan_to_script(
        plan,
        video_title=yt_title,
        video_duration_sec=duration_sec,
        source_channel=yt_channel,
        source_title=yt_title,
        youtube_url=url,
    )
    print(f"✅ 스크립트 변환 완료 ({len(script.scenes)}씬, {script.metadata.duration}초)", file=sys.stderr)

    # Render: Gemini TTS + scene clip cut + Remotion
    print(f"🎙️ Gemini TTS Charon 합성 중...", file=sys.stderr)
    try:
        from src.tts.gemini_tts_generator import (
            GeminiTTSError,
            generate_voice_with_timing_gemini,
        )
        audio_path, timings = generate_voice_with_timing_gemini(
            script,
            voice_name="Charon",
            style_prompt="Read in a fast, clear newscaster tone with neutral political delivery:",
            temperature=0.5,
            include_outro=False,
        )
    except GeminiTTSError as e:
        print(f"❌ Gemini TTS 실패: {e}", file=sys.stderr)
        return 6
    print(f"✅ 음성 합성 완료", file=sys.stderr)

    print(f"✂️ 씬 클립 분할 (9:16)...", file=sys.stderr)
    from src.dem_shorts.editor.segment_cutter import cut_segment
    main_timings = [t for t in timings if t["scene_id"] != -1]
    if not main_timings:
        print("❌ 씬 타이밍 비어 있음", file=sys.stderr)
        return 7
    tts_total_ms = max(t["end_ms"] for t in main_timings)
    clip_duration = plan.clip_end_sec - plan.clip_start_sec
    import time as _time
    ts2 = int(_time.time())
    scene_videos = []
    for t in main_timings:
        sid = t["scene_id"]
        ns = plan.clip_start_sec + (t["start_ms"] / tts_total_ms) * clip_duration
        ne = plan.clip_start_sec + (t["end_ms"] / tts_total_ms) * clip_duration
        out_file = out_dir / f"scene_{ts2}_{sid:02d}.mp4"
        # political_pro: TTS가 메인 음성이므로 영상 음성은 mute (중첩·에코 방지)
        cut_segment(input_path=vp, output_path=out_file, start_sec=ns, end_sec=ne, mute=True)
        scene_videos.append({"scene_id": sid, "video_path": str(out_file)})
    print(f"✅ 씬 클립 {len(scene_videos)}개 분할 완료", file=sys.stderr)

    print(f"🎬 Remotion 렌더 중...", file=sys.stderr)
    try:
        from src.video.renderer import render_video
        mp4 = render_video(
            script,
            audio_path=audio_path,
            scene_videos=scene_videos,
            use_bgm=not args.no_bgm,
            scene_timings=timings,
            # political_pro: 뉴스 톤. 화면 전환 효과(fade/slide/zoom) + 전환 효과음
            # (whoosh/impact 등) 모두 강제 OFF. 사용자 --no-* 인자와 무관 (정치 모드 컨벤션).
            enable_transitions=False,
            enable_sfx=False,
        )
    except Exception as e:
        print(f"❌ 렌더 실패: {e}", file=sys.stderr)
        return 7

    size_mb = mp4.stat().st_size / (1024 * 1024)
    print(f"\n📁 출력: {mp4} ({size_mb:.1f}MB, {script.metadata.duration:.0f}s)", file=sys.stderr)
    print(
        "⚠️  주의: 출력은 자동 생성 결과입니다. 게시 전 반드시 사용자 검수가 필요합니다.",
        file=sys.stderr,
    )
    print(str(mp4))  # stdout: 최종 mp4 경로 (스크립팅용)
    return 0


def cmd_daily_briefing(args: argparse.Namespace) -> int:
    """매일 정치 이슈 자동 브리핑 + 기획안 (Feature 020).

    어제(KST) YouTube 정치 채널 + 네이버 뉴스 → 클러스터링 → 점수화 →
    상위 N개 이슈에 generate_three_plans 자동 호출.
    """
    print("🗞️  매일 정치 이슈 브리핑 시작...", file=sys.stderr)
    try:
        from src.briefing.plan_runner import run_briefing
        result = run_briefing(top_n=args.top, date_str=args.date)
    except Exception as e:
        print(f"\n❌ 브리핑 실패: {e}", file=sys.stderr)
        return 1

    print(
        f"\n✅ 브리핑 완료 — date={result.date}, "
        f"채널 {result.channel_count}개, "
        f"영상 {result.raw_video_count}개, "
        f"기사 {result.raw_news_count}개 수집",
        file=sys.stderr,
    )
    print(f"\n📊 상위 {min(args.top, len(result.ranked_issues))} 이슈:", file=sys.stderr)
    for ri in result.ranked_issues[: args.top]:
        topv = ri.cluster.top_video
        print(
            f"  [{ri.rank}] score={ri.score:>10,.0f}  "
            f"{ri.cluster.topic}  "
            f"(영상 {len(ri.cluster.videos)}, 기사 {len(ri.cluster.news)})",
            file=sys.stderr,
        )
        if topv:
            print(
                f"        대표: {topv.url}  ({topv.view_count:,}회 · {topv.comment_count:,}댓글)",
                file=sys.stderr,
            )
    from src.briefing.plan_runner import BRIEFING_DATA_DIR
    print(
        f"\n📁 결과: {BRIEFING_DATA_DIR / result.date}",
        file=sys.stderr,
    )
    return 0


def cmd_celebrity(args: argparse.Namespace) -> int:
    """Handle the 'celebrity' subcommand — 유명인 이름 → 소개 쇼츠 (학습 목적 전용).

    2-phase flow (2026-04-21):
      --analyze-only: Step 1~2 (namuwiki fetch + Claude script)만 실행 후 종료.
                      stdout 마지막 줄에 JSON `{"script_path": "...", "name": "..."}`
                      을 출력해 UI에서 파싱 가능.
      --from-script PATH: Step 1~2 스킵. 저장된 script.json + 원본 CelebrityInfo
                          (namuwiki cache)를 로드해 Step 3~6만 실행.
      둘 다 없으면: 기존 end-to-end 실행 (하위호환).
    """
    import json as _json
    from src.analyzer.celebrity_analyzer import analyze_celebrity
    from src.analyzer.claude_analyzer import AnalyzerError
    from src.analyzer.script_models import ShortsScript
    from src.scraper.namuwiki_scraper import NamuwikiScraper, NamuwikiScraperError
    from src.video.renderer import RenderError, render_video

    try:
        name = (args.name or "").strip()
        if not name:
            print("\n❌ 인물 이름을 입력하세요", file=sys.stderr)
            return 1

        from_script = getattr(args, "from_script", None)
        analyze_only = getattr(args, "analyze_only", False)
        qualifier = (getattr(args, "qualifier", None) or "").strip() or None

        # ── Step 1~2: namuwiki + Claude script (from_script면 스킵) ──
        if from_script:
            # Phase 2 진입: 이미 생성·편집된 script.json을 로드
            script_path = Path(from_script).resolve()
            if not script_path.exists():
                print(f"\n❌ --from-script 경로 없음: {script_path}", file=sys.stderr)
                return 1
            print(f"📂 기존 script 로드: {script_path}")
            script = ShortsScript.from_dict(
                _json.loads(script_path.read_text(encoding="utf-8"))
            )
            # namuwiki 정보는 캐시에서 로드 (source_url용)
            scraper = NamuwikiScraper()
            info = scraper.fetch_person(name, qualifier=qualifier)
        else:
            # Step 1: Namuwiki fetch
            label = f"{name}({qualifier})" if qualifier else name
            print(f"📚 Step 1/6: 나무위키에서 '{label}' 정보 조회 중...")
            scraper = NamuwikiScraper()
            info = scraper.fetch_person(name, qualifier=qualifier)
            print(f"   요약: {info.summary[:60]}")
            print(f"   경력 {len(info.career_highlights)}건 / 여담 {len(info.trivia)}건")

            # Step 2: Script generation
            print("📝 Step 2/6: 대본 생성 중...")
            script, script_path = analyze_celebrity(info, qualifier=qualifier)
            print(
                f"   감정: {script.metadata.emotion_type} | "
                f"씬: {len(script.scenes)}개 | "
                f"길이: {script.metadata.duration}초"
            )
            print(f"   저장: {script_path}")

        # ── --analyze-only: Phase 1 종료 ──
        if analyze_only:
            # 씬마다 1장씩 이미지 다운로드 (사용자 요청 2026-04-21 v3)
            scene_images = _download_celebrity_scene_images(
                name, script, qualifier=qualifier,
            )
            payload = {
                "script_path": str(script_path),
                "name": name,
                "title": script.metadata.title,
                "emotion": script.metadata.emotion_type,
                "duration": script.metadata.duration,
                "scene_count": len(script.scenes),
                "source_url": info.source_url,
                "scene_images": scene_images,  # [{"scene_id": N, "path": "...", "filename": "...", "query": "..."}, ...]
            }
            print("ANALYZE_DONE " + _json.dumps(payload, ensure_ascii=False))
            return 0

        video_source = getattr(args, "video_source", "freepik")
        clip_crop_mode = getattr(args, "clip_crop", "crop")

        if video_source == "youtube":
            # ── YouTube 소스 플로우: TTS → YouTube 클립 → Render ──
            print("🎙️  Step 4/6: 음성 합성 중... (YouTube 클립 싱크용)")
            tts_code, voice_path, scene_timings = _run_tts(script)
            if tts_code != 0:
                print("   ⚠️  TTS 실패, 무음 영상으로 계속합니다.")
                voice_path = None
                scene_timings = None

            print("📹 Step 5/6: YouTube 클립 다운로드 및 9:16 컷...")
            video_paths = _run_celebrity_youtube_clips(
                name, script, scene_timings=scene_timings, crop_mode=clip_crop_mode,
            )
            if video_paths:
                print(f"   ✅ {len(video_paths)}개 씬 클립 준비 완료")
            else:
                print("   ⚠️  YouTube 클립 실패 — 그라데이션 배경으로 렌더링합니다.")

            # source_label 주입 (없는 경우)
            if not script.metadata.source_label:
                from src.analyzer.script_models import Metadata as _Metadata
                from src.analyzer.script_models import ShortsScript as _SS
                new_meta = _Metadata(
                    title=script.metadata.title,
                    emotion_type=script.metadata.emotion_type,
                    duration=script.metadata.duration,
                    source_url=script.metadata.source_url,
                    source_type=script.metadata.source_type,
                    source_label="출처: YouTube",
                )
                script = _SS(
                    metadata=new_meta,
                    scenes=script.scenes,
                    audio=script.audio,
                    background=script.background,
                )

            use_bgm = not getattr(args, "no_bgm", False)
            enable_transitions = not getattr(args, "no_transitions", False)
            enable_sfx = not getattr(args, "no_sfx", False)
            print("🎬 Step 6/6: 영상 렌더링 중...")
            output_path = render_video(
                script,
                audio_path=voice_path,
                scene_videos=video_paths,
                scene_timings=scene_timings,
                use_bgm=use_bgm,
                enable_transitions=enable_transitions,
                enable_sfx=enable_sfx,
                speed_multiplier=1.2,
            )
            image_paths = None
        else:
            # ── Freepik 소스 플로우 (기존) ──

            # Step 3: Images — priority: scene-images-json > portrait-path > auto 검색
            image_paths: list[dict] | None = None
            if not getattr(args, "no_images", False):
                scene_images_json = getattr(args, "scene_images_json", None)
                portrait_path = getattr(args, "portrait_path", None)
                if scene_images_json and Path(scene_images_json).exists():
                    # 사용자가 검수 화면에서 씬별 지정한 경로 맵 로드
                    print(f"🖼️  Step 3/6: 사용자 씬별 이미지 맵 사용 — {scene_images_json}")
                    raw_map = _json.loads(Path(scene_images_json).read_text(encoding="utf-8"))
                    # key가 str일 수 있으니 int/str 모두 허용
                    scene_map = {int(k): v for k, v in raw_map.items() if v}
                    image_paths = []
                    for s in script.scenes:
                        path = scene_map.get(s.id)
                        if path and Path(path).exists():
                            image_paths.append({
                                "scene_id": s.id, "image_path": path,
                                "prompt": "(user selected)",
                            })
                    if not image_paths:
                        print("   ⚠️  맵에서 유효한 경로 없음 — 재검색으로 폴백")
                        image_paths = None
                elif portrait_path and Path(portrait_path).exists():
                    print(f"🖼️  Step 3/6: 사용자 선택 이미지 사용 — {portrait_path}")
                    image_paths = [
                        {"scene_id": s.id, "image_path": portrait_path, "prompt": "(user selected)"}
                        for s in script.scenes
                    ]
                if image_paths is None:
                    single_portrait = not getattr(args, "symbolic_images", False)
                    image_paths = _run_celebrity_images(
                        name, script, qualifier=qualifier,
                        single_portrait=single_portrait,
                    )

            # Step 4: Image-to-video (Freepik) — optional
            video_paths: list[dict] | None = None
            if (
                not getattr(args, "no_video", False)
                and image_paths
                and len(image_paths) > 0
            ):
                # Freepik 2026-04 정책 변경으로 image-to-video가 모두 유료.
                # Premium+ 크레딧 소모 허용 (원치 않으면 --no-paid-credits로 차단).
                allow_paid = not getattr(args, "no_paid_credits", False)
                video_paths = _run_celebrity_videos(
                    name, script, image_paths, allow_paid=allow_paid,
                )

            # Step 5: TTS
            print("🎙️  Step 5/6: 음성 생성 중...")
            tts_code, voice_path, scene_timings = _run_tts(script)
            if tts_code != 0:
                print("   ⚠️  TTS 실패, 무음 영상으로 계속합니다.")
                voice_path = None
                scene_timings = None

            # Step 6: Render
            print("🎬 Step 6/6: 영상 렌더링 중...")
            use_bgm = not getattr(args, "no_bgm", False)
            enable_transitions = not getattr(args, "no_transitions", False)
            enable_sfx = not getattr(args, "no_sfx", False)
            output_path = render_video(
                script,
                audio_path=voice_path,
                scene_images=None if video_paths else image_paths,
                scene_videos=video_paths,
                scene_timings=scene_timings,
                use_bgm=use_bgm,
                enable_transitions=enable_transitions,
                enable_sfx=enable_sfx,
                speed_multiplier=1.2,
            )

        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 완료! '{name}' 소개 쇼츠 생성")
        print(f"   영상: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        print(f"   출처: {info.source_url}")
        print("   ℹ️  학습 목적 전용 — 공개 업로드 전 초상권/저작권 확인 필요")

        # 결과 화면이 씬별 UI를 구성할 수 있도록 경로 맵을 stdout에 JSON으로 출력
        render_payload = {
            "script_path": str(script_path),
            "audio_path": str(voice_path) if voice_path else "",
            "scene_images": [
                {"scene_id": d["scene_id"], "path": d["image_path"]}
                for d in (image_paths or [])
            ],
            "scene_videos": [
                {"scene_id": d["scene_id"], "path": d["video_path"]}
                for d in (video_paths or [])
            ],
        }
        print("RENDER_DONE " + _json.dumps(render_payload, ensure_ascii=False))
        return 0

    except (NamuwikiScraperError, AnalyzerError, RenderError) as e:
        logger.error("유명인 파이프라인 오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error("유명인 파이프라인 예상치 못한 오류: %s", e, exc_info=True)
        print(f"\n❌ 예상치 못한 오류: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        return 130


def _run_celebrity_images(
    name: str, script, qualifier: str | None = None,
    *, single_portrait: bool = True,
) -> list[dict] | None:
    """씬별 이미지 확보 로직. 2가지 모드 지원.

    Phase 9 v3 (2026-04-21 v2): 사용자 피드백 반영 —
    Freepik image-to-video는 이미지 얼굴만 유지한 채 작은 모션을 붙이기 때문에
    씬별로 다른 상징 이미지(판사봉·국회의사당…)를 쓰면 "전혀 무관한 영상"처럼 보임.

    Args:
        single_portrait (default True): 인물 얼굴 1장을 다운로드해 모든 씬에서 공유.
            → Freepik 영상이 "인물이 말하는/응시하는" 톤으로 일관되게 생성.
            이미지는 `data/celebrity_portraits/{name}_{ts}.jpg`에 영구 저장.
        single_portrait=False: 기존 씬별 image_query 방식 (상징 이미지 다양화).

    qualifier: 동명이인 구분용 (예: "정치인"). 쿼리에 자동 결합.

    Returns scene_images list or None (전체 실패 시).
    """
    if single_portrait:
        return _run_celebrity_portrait_mode(name, script, qualifier=qualifier)
    return _run_celebrity_symbolic_mode(name, script, qualifier=qualifier)


def _run_celebrity_portrait_mode(
    name: str, script, qualifier: str | None = None,
) -> list[dict] | None:
    """인물 대표 사진 1장을 다운로드해 모든 씬에 동일 이미지 주입."""
    from datetime import datetime
    from src.config.settings import DATA_DIR
    from src.illustrator.naver_image_search import (
        NaverImageSearcher,
        NaverImageSearchError,
    )

    portrait_dir = DATA_DIR / "celebrity_portraits"
    portrait_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]
    query = f"{name} {qualifier}".strip() if qualifier else name

    print(f"🖼️  Step 3/6: 인물 대표 이미지 다운로드 ('{query}' 1장, 전 씬 공유)...")
    try:
        searcher = NaverImageSearcher()
        # 첫 이미지가 저품질일 수 있어 3장 받고 최대 크기·확장자 우선으로 고름
        results = searcher.search(query, count=3)
        saved = searcher.download(
            results, portrait_dir, filename_prefix=f"{safe_name}_{timestamp}",
        )
    except NaverImageSearchError as exc:
        logger.warning("인물 이미지 검색 실패: %s", exc)
        print(f"   ⚠️  인물 이미지 검색 실패: {exc} — 그라데이션 배경 사용")
        return None

    if not saved:
        print("   ⚠️  이미지 결과 없음 — 그라데이션 배경 사용")
        return None

    portrait_path = saved[0]
    print(f"   저장: {portrait_path.name}")

    return [
        {"scene_id": scene.id, "image_path": str(portrait_path), "prompt": query}
        for scene in script.scenes
    ]


def _run_celebrity_symbolic_mode(
    name: str, script, qualifier: str | None = None,
) -> list[dict] | None:
    """[기존] 씬별 image_query 에 따라 네이버 이미지 검색 + 다운로드.

    Phase 9 v2 (2026-04-21): 씬마다 다른 쿼리 지원. "서울대를 졸업했다" 씬이면
    scene.image_query="서울대학교 정문"으로 검색해 해당 이미지를 받는다.
    None이면 인물명으로 폴백. 동일 쿼리는 한 번만 API 호출 후 재사용.

    qualifier 주면 "인물 자체"를 검색하는 씬(query에 인물명 단독으로 있을 때)에
    qualifier를 붙여 동명이인 오염 방지.

    Returns scene_images list or None (전체 실패 시).
    """
    from datetime import datetime
    from src.config.settings import DATA_DIR
    from src.illustrator.naver_image_search import (
        NaverImageSearcher,
        NaverImageSearchError,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]
    output_dir = DATA_DIR / "images" / "celebrity" / f"{timestamp}_{safe_name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🖼️  Step 3/6: 네이버 이미지 검색 ({len(script.scenes)}씬, 씬별 쿼리)...")
    searcher = NaverImageSearcher()
    scene_images: list[dict] = []
    query_cache: dict[str, list] = {}  # query → downloaded paths
    query_cursor: dict[str, int] = {}  # query → next path index

    for scene in script.scenes:
        query = (scene.image_query or "").strip() or name
        # qualifier 있고 query가 인물명만 쓰는 경우 구분자 추가
        if qualifier and query == name:
            query = f"{name} {qualifier}"
        try:
            if query not in query_cache:
                results = searcher.search(query, count=3)
                safe_q = "".join(c if c.isalnum() else "_" for c in query)[:30] or "q"
                saved = searcher.download(
                    results, output_dir,
                    filename_prefix=f"{safe_q}_{scene.id:02d}",
                )
                query_cache[query] = list(saved)
                query_cursor[query] = 0
                print(f"   씬 {scene.id}: '{query}' → {len(saved)}장")

            cache = query_cache[query]
            idx = query_cursor[query]
            if not cache:
                # 해당 쿼리에서 아무것도 못 받음 — 이 씬은 스킵 (그라데이션)
                continue
            path = cache[idx % len(cache)]
            query_cursor[query] = idx + 1
            scene_images.append({
                "scene_id": scene.id,
                "image_path": str(path),
                "prompt": query,
            })
        except NaverImageSearchError as e:
            logger.warning("씬 %d '%s' 검색 실패: %s", scene.id, query, e)
            print(f"   ⚠️  씬 {scene.id}: '{query}' 실패 — 그라데이션 폴백")

    if not scene_images:
        print("   ⚠️  모든 씬 이미지 검색 실패, 그라데이션 배경으로 대체")
        return None
    print(f"   완료: {len(scene_images)}/{len(script.scenes)} 씬 이미지 확보")
    return scene_images


def _run_celebrity_videos(
    name: str, script, image_paths: list[dict], *, allow_paid: bool = True,
) -> list[dict] | None:
    """Convert each portrait to a 5s clip via Freepik. Returns scene_videos or None.

    2026-04-21 Freepik 정책 변경: Wan 2.2 모델이 UI에서 제거됐고, Kling 2.5 768p
    옵션도 사라져 모든 image-to-video가 유료가 됨 (MiniMax ~150, Kling ~325 크레딧/클립).
    Premium+ 월 크레딧으로 감당 가능하므로 기본 allow_paid=True로 호출한다.
    credit 소모 원치 않으면 CLI에서 `--no-video`로 전체 스킵.
    """
    import asyncio
    from datetime import datetime
    from src.config.settings import DATA_VIDEOS_DIR
    from src.video_gen.base import VideoGenerationError
    from src.video_gen.celebrity_motion import build_celebrity_motion_prompt
    from src.video_gen.factory import create_generator

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]
    output_dir = DATA_VIDEOS_DIR / "celebrity" / f"{timestamp}_{safe_name}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎥 Step 4/6: Freepik 영상 변환 ({len(image_paths)}씬)...")
    try:
        gen = create_generator("freepik")
    except Exception as e:
        logger.warning("Freepik 초기화 실패: %s", e)
        print(f"   ⚠️  Freepik 초기화 실패: {e}")
        return None

    results: list[dict] = []
    scene_by_id = {scene.id: scene for scene in script.scenes}

    for idx, img in enumerate(image_paths, start=1):
        scene = scene_by_id.get(img["scene_id"])
        if scene is None:
            continue
        motion = build_celebrity_motion_prompt(scene, name)
        output_path = output_dir / f"scene_{scene.id:02d}.mp4"
        try:
            asyncio.run(
                gen.generate_and_wait(
                    prompt=motion,
                    duration=min(scene.duration, 5.0),
                    source_image=img["image_path"],
                    output_path=str(output_path),
                    allow_paid=allow_paid,
                )
            )
            results.append({"scene_id": scene.id, "video_path": str(output_path)})
            print(f"   ✓ 씬 {idx}/{len(image_paths)}")
        except VideoGenerationError as e:
            logger.warning("씬 %d 영상 생성 실패: %s", scene.id, e)
            print(f"   ⚠️  씬 {idx} 실패 (스킵): {e}")
            continue

    return results if results else None


def _build_celebrity_clip_keywords(name: str, script) -> list[str]:
    """씬별 YouTube 검색어 빌드. 우선순위: clip_query → image_query+name → name."""
    from src.scraper.youtube_news_searcher import safe_search_keyword
    keywords = []
    for scene in script.scenes:
        if scene.clip_query:
            keywords.append(safe_search_keyword(scene.clip_query))
        elif scene.image_query:
            keywords.append(safe_search_keyword(f"{name} {scene.image_query}"))
        else:
            keywords.append(safe_search_keyword(name))
    return keywords


def _run_celebrity_youtube_clips(
    name: str,
    script,
    *,
    scene_timings: list[dict] | None = None,
    crop_mode: str = "crop",
) -> list[dict] | None:
    """유튜브 클립을 씬별 다운로드·컷. [{scene_id, video_path}, ...] or None."""
    import time as _time
    from src.config.settings import DATA_VIDEOS_DIR
    from src.scraper.youtube_news_searcher import build_scene_clips

    safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]
    ts = int(_time.time())
    out_dir = DATA_VIDEOS_DIR / "celebrity" / f"{ts}_{safe_name}"

    keywords = _build_celebrity_clip_keywords(name, script)

    # scene_durations: timing 기반이면 TTS 실제 길이, 없으면 scene.duration
    if scene_timings:
        timing_map = {
            t["scene_id"]: (t["end_ms"] - t["start_ms"]) / 1000.0
            for t in scene_timings if t.get("scene_id", -1) != -1
        }
        scene_durations = [timing_map.get(s.id, s.duration) for s in script.scenes]
    else:
        scene_durations = [s.duration for s in script.scenes]

    try:
        clips = build_scene_clips(
            scene_durations,
            keywords=keywords,
            out_dir=out_dir,
            crop_mode=crop_mode,
        )
    except Exception as e:
        logger.warning("YouTube 클립 다운로드 실패: %s", e)
        return None

    result = []
    for scene, clip in zip(script.scenes, clips):
        if clip is not None and clip.exists():
            result.append({"scene_id": scene.id, "video_path": str(clip)})

    return result if result else None


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="contentsmaker",
        description="블라인드 인기글 → 쇼츠 영상 자동 생성 파이프라인",
    )
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # image subcommand
    image_parser = subparsers.add_parser(
        "image", help="블라인드 스크린샷 → 영상 자동 생성 (이미지 1장 이상)"
    )
    image_parser.add_argument(
        "images", nargs="+", type=str,
        help="블라인드 스크린샷 이미지 경로 (여러 장 가능)"
    )
    image_parser.add_argument(
        "--no-references", action="store_true",
        help="레퍼런스 이미지 비활성화 (기본: data/references/ 자동 사용)"
    )
    image_parser.add_argument(
        "--no-bgm", action="store_true",
        help="배경음악 비활성화 (기본: 감정별 BGM 자동 삽입)"
    )

    # manual subcommand
    manual_parser = subparsers.add_parser(
        "manual", help="수동으로 블라인드 글 입력"
    )
    manual_group = manual_parser.add_mutually_exclusive_group(required=True)
    manual_group.add_argument("--file", "-f", type=str, help="JSON 파일 경로")
    manual_group.add_argument("--interactive", "-i", action="store_true", help="대화형 입력 모드")

    # analyze subcommand
    analyze_parser = subparsers.add_parser(
        "analyze", help="블라인드 글 → 쇼츠 스크립트 변환 (Claude Code)"
    )
    analyze_parser.add_argument("--file", "-f", type=str, required=True, help="raw_content.json 경로")
    analyze_parser.add_argument("--with-tts", action="store_true", help="분석 후 TTS도 함께 실행")

    # tts subcommand
    tts_parser = subparsers.add_parser(
        "tts", help="스크립트 → 음성 변환 (edge-tts 또는 Gemini)"
    )
    tts_parser.add_argument("--file", "-f", type=str, required=True, help="script.json 경로")
    tts_parser.add_argument(
        "--provider",
        choices=["edge", "gemini"],
        default="gemini",
        help="TTS 공급자 (기본: gemini, Google AI Studio). GEMINI_API_KEY 없으면 edge로 자동 폴백.",
    )
    tts_parser.add_argument(
        "--voice",
        type=str,
        default=None,
        help="Gemini 보이스 이름 (기본: Leda). edge 공급자에서는 무시됩니다.",
    )

    # render subcommand
    render_parser = subparsers.add_parser(
        "render", help="스크립트 + 음성 → 영상 렌더링 (Remotion)"
    )
    render_parser.add_argument("--script", "-s", type=str, required=True, help="script.json 경로")
    render_parser.add_argument("--audio", "-a", type=str, help="voice.mp3 경로 (선택)")

    # pipeline subcommand
    pipeline_parser = subparsers.add_parser(
        "pipeline", help="전체 파이프라인: raw → 분석 → TTS → 영상"
    )
    pipeline_parser.add_argument("--file", "-f", type=str, required=True, help="raw_content.json 경로")
    pipeline_parser.add_argument(
        "--no-references", action="store_true",
        help="레퍼런스 이미지 비활성화 (기본: data/references/ 자동 사용)"
    )
    pipeline_parser.add_argument(
        "--no-bgm", action="store_true",
        help="배경음악 비활성화 (기본: 감정별 BGM 자동 삽입)"
    )

    # celebrity subcommand — Phase 9 유명인 소개 쇼츠
    celebrity_parser = subparsers.add_parser(
        "celebrity",
        help="유명인 이름 → 나무위키 정보 → 소개 쇼츠 (학습 목적 전용)",
    )
    celebrity_parser.add_argument("name", type=str, help="인물 이름 (예: 손흥민)")
    celebrity_parser.add_argument(
        "--qualifier", type=str, default=None,
        help="동명이인 구분자 (예: '정치인', '배우', '축구선수'). 나무위키에서 "
             "'{이름}({qualifier})' 페이지를 먼저 시도하고 Naver 검색에도 결합.",
    )
    celebrity_parser.add_argument(
        "--no-video", action="store_true",
        help="Freepik image-to-video 스킵, 정지 이미지로 렌더링",
    )
    celebrity_parser.add_argument(
        "--no-images", action="store_true",
        help="이미지 없이 그라데이션 배경만 사용",
    )
    celebrity_parser.add_argument(
        "--no-bgm", action="store_true",
        help="배경음악 비활성화",
    )
    celebrity_parser.add_argument(
        "--no-transitions", action="store_true",
        help="화면 전환 효과(punch-zoom 등) 비활성화",
    )
    celebrity_parser.add_argument(
        "--no-sfx", action="store_true",
        help="효과음(whoosh·impact 등) 비활성화",
    )
    celebrity_parser.add_argument(
        "--no-paid-credits", action="store_true",
        help="Freepik 유료 크레딧 차감 금지 (2026-04 정책 변경 후 image-to-video는 "
             "모두 유료이므로 기본은 허용). 이 플래그 켜면 크레딧 비용 있으면 에러.",
    )
    celebrity_parser.add_argument(
        "--analyze-only", action="store_true",
        help="Phase 1만 실행 (namuwiki + Claude 대본). 씬 편집 전 리뷰용.",
    )
    celebrity_parser.add_argument(
        "--from-script", type=str, metavar="PATH",
        help="Phase 2만 실행 — 지정한 script.json으로 images/TTS/렌더만 돌림.",
    )
    celebrity_parser.add_argument(
        "--symbolic-images", action="store_true",
        help="씬별 image_query 기반 상징 이미지 사용 (기본: 인물 대표 사진 1장 공유).",
    )
    celebrity_parser.add_argument(
        "--portrait-path", type=str, metavar="PATH",
        help="[Legacy] 대표 이미지 1장을 모든 씬에 공유. "
             "scene-images-json이 더 세밀한 씬별 제어를 제공.",
    )
    celebrity_parser.add_argument(
        "--scene-images-json", type=str, metavar="PATH",
        help="사용자가 검수 화면에서 씬별 지정·업로드한 이미지 경로 JSON 맵 "
             "({\"1\": \"/path/a.jpg\", \"2\": ...}). 지정 시 네이버 재검색 없이 이 "
             "파일들을 각 씬에 주입.",
    )
    celebrity_parser.add_argument(
        "--image-gem", type=str, metavar="KEY", default=None,
        help="이미지 생성에 사용할 Gem 키 (e.g. webtoon). "
             "지정 시 해당 Gem으로 이동 후 씬 내용만 전송.",
    )
    celebrity_parser.add_argument(
        "--video-gem", type=str, metavar="KEY", default=None,
        help="영상 생성에 사용할 Gem 키 (e.g. news, drama).",
    )
    celebrity_parser.add_argument(
        "--video-source",
        choices=["freepik", "youtube"],
        default="freepik",
        help="영상 소스: freepik(기본, Freepik image-to-video) | youtube(YouTube 클립 자동 검색·컷)",
    )
    celebrity_parser.add_argument(
        "--clip-crop",
        choices=["crop", "letterbox"],
        default="crop",
        dest="clip_crop",
        help="YouTube 클립 9:16 처리 방식: crop(기본, 중앙 크롭) | letterbox(위아래 검은 여백)",
    )

    # political-pro subcommand — Feature 009 (정치 숏츠 기획자)
    political_pro_parser = subparsers.add_parser(
        "political-pro",
        help="정치 YouTube 영상 → 3 기획안(RTF 6요소) → 1 선택 → 9:16 쇼츠",
    )
    political_pro_parser.add_argument(
        "youtube_url", type=str, nargs="?", default="",
        help="YouTube URL (source-type=youtube 일 때 필수, topic 일 때 무시)",
    )
    political_pro_parser.add_argument(
        "--source-type", type=str, choices=["youtube", "topic"], default="youtube",
        help="입력 소스: youtube(기존) / topic(주제 텍스트만, Feature 023)",
    )
    political_pro_parser.add_argument(
        "--topic", type=str, default="",
        help="주제 텍스트 (source-type=topic 일 때 필수)",
    )
    political_pro_parser.add_argument(
        "--tone", type=str, default="분노·격앙",
        help="기획 톤 (source-type=topic 일 때 사용). 기본: '분노·격앙'",
    )
    political_pro_parser.add_argument(
        "--details", type=str, default="",
        help="추가 상세 정보 (source-type=topic 일 때 사용)",
    )
    political_pro_parser.add_argument(
        "--plan-idx", type=int, choices=[0, 1, 2], default=None,
        help="비인터랙티브 모드: 사용할 plan 인덱스 (0/1/2)",
    )
    political_pro_parser.add_argument(
        "--interactive", action="store_true",
        help="3개 plan 표시 후 stdin으로 선택 입력 받음",
    )
    political_pro_parser.add_argument(
        "--plans-only", action="store_true",
        help="기획안만 출력하고 종료 (영상 생성 안 함)",
    )
    political_pro_parser.add_argument(
        "--no-bgm", action="store_true", help="배경음악 비활성화",
    )
    political_pro_parser.add_argument(
        "--no-transitions", action="store_true", help="화면 전환 효과 비활성화",
    )
    political_pro_parser.add_argument(
        "--no-sfx", action="store_true", help="효과음 비활성화",
    )
    political_pro_parser.add_argument(
        "--video-gem", type=str, metavar="KEY", default=None,
        help="영상 생성에 사용할 Gem 키 (e.g. news, drama).",
    )

    # crawl subcommand (P2 placeholder)
    # url subcommand
    url_parser = subparsers.add_parser(
        "url", help="게시글 URL → 영상 자동 생성 (디시/네이트판/네이버카페)"
    )
    url_parser.add_argument("url", type=str, help="게시글 URL")
    url_parser.add_argument(
        "--no-references", action="store_true",
        help="레퍼런스 이미지 비활성화"
    )
    url_parser.add_argument(
        "--no-bgm", action="store_true",
        help="배경음악 비활성화"
    )

    # youtube-auth subcommand
    subparsers.add_parser(
        "youtube-auth", help="YouTube API OAuth 인증 (최초 1회)"
    )

    # daily-briefing subcommand (Feature 020) — 매일 정치 이슈 자동 브리핑
    briefing_parser = subparsers.add_parser(
        "daily-briefing",
        help="어제(KST) 정치 YouTube + 네이버 뉴스 → 핫한 순 N개 이슈 기획안 자동 생성",
    )
    briefing_parser.add_argument(
        "--top", type=int, default=5,
        help="기획안 생성할 상위 이슈 수 (default: 5)",
    )
    briefing_parser.add_argument(
        "--date", type=str, default=None,
        help="명시적 어제 날짜 (YYYY-MM-DD). 미지정 시 KST 기준 자동 계산",
    )

    # tiktok-auth subcommand
    subparsers.add_parser(
        "tiktok-auth", help="TikTok API OAuth 인증 (최초 1회)"
    )

    subparsers.add_parser("crawl", help="블라인드 URL 자동 크롤링 (미구현)")

    # deevid_login subcommand
    subparsers.add_parser(
        "deevid_login",
        help="deevid.ai 1회 수동 로그인 (브라우저 자동화 영상 생성용)",
    )

    # freepik_login subcommand
    subparsers.add_parser(
        "freepik_login",
        help="Freepik 1회 수동 로그인 (브라우저 자동화 영상 생성용)",
    )

    # gemini_login subcommand (Phase 2A/2B: Imagen 4 + Veo 3 web automation)
    subparsers.add_parser(
        "gemini_login",
        help="gemini.google.com 1회 수동 로그인 (Imagen 4 / Veo 3 자동화용)",
    )

    # gems subcommand — Gemini Gems 프롬프트 프리셋 관리
    gems_parser = subparsers.add_parser(
        "gems",
        help="Gemini Gems 프리셋 관리 (list / show-prompt)",
    )
    gems_sub = gems_parser.add_subparsers(dest="gems_action")
    gems_sub.add_parser("list", help="등록된 Gem 목록 출력")
    gems_show = gems_sub.add_parser(
        "show-prompt",
        help="Gem 지침 텍스트 출력 (Gemini Gem 생성 시 붙여넣기용)",
    )
    gems_show.add_argument(
        "key",
        type=str,
        help="Gem 키 (e.g. webtoon, news, drama)",
    )
    gems_show.add_argument(
        "--kind",
        choices=["image", "video"],
        default="image",
        help="Gem 종류 (기본: image)",
    )

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "image": cmd_image,
        "manual": cmd_manual,
        "analyze": cmd_analyze,
        "tts": cmd_tts,
        "render": cmd_render,
        "pipeline": cmd_pipeline,
        "url": cmd_url,
        "celebrity": cmd_celebrity,
        "political-pro": cmd_political_pro,
        "daily-briefing": cmd_daily_briefing,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    if args.command == "youtube-auth":
        from src.upload.youtube_uploader import authenticate, UploadError
        try:
            authenticate()
            return 0
        except UploadError as e:
            print(f"\n❌ {e}", file=sys.stderr)
            return 1

    if args.command == "tiktok-auth":
        from src.upload.tiktok_uploader import authenticate, TikTokUploadError
        try:
            authenticate()
            return 0
        except TikTokUploadError as e:
            print(f"\n❌ {e}", file=sys.stderr)
            return 1

    if args.command == "crawl":
        print("⚠️  자동 크롤링은 아직 구현되지 않았습니다")
        return 1

    if args.command == "deevid_login":
        from src.video_gen.deevid_gen import run_interactive_login
        return run_interactive_login()

    if args.command == "freepik_login":
        from src.video_gen.freepik_gen import run_interactive_login as freepik_login
        return freepik_login()

    if args.command == "gemini_login":
        from src.illustrator.gemini_web_login import run_interactive_login as gemini_login
        return gemini_login()

    if args.command == "gems":
        return _cmd_gems(args)

    return 0


def _cmd_gems(args: argparse.Namespace) -> int:
    """Gemini Gems 프리셋 관리 커맨드."""
    from src.illustrator.gem_navigator import (
        list_gems,
        get_gem_config,
        get_system_prompt_text,
        GemNotFoundError,
    )

    action = getattr(args, "gems_action", None)

    if not action or action == "list":
        gems = list_gems()
        print("\n📋 등록된 Gemini Gems 프리셋\n")
        for kind, items in gems.items():
            label = "🖼️  이미지 Gems" if kind == "image" else "🎬 영상 Gems"
            print(f"{label}")
            if not items:
                print("  (없음)")
            for item in items:
                print(f"  [{item['key']}]  {item['gem_name']}  —  {item['description']}")
        print()
        print("사용 예시:")
        print("  python3 -m src.main celebrity 손흥민 --image-gem webtoon")
        print("  python3 -m src.main political-pro URL --video-gem news")
        print()
        print("Gem 지침 보기:")
        print("  python3 -m src.main gems show-prompt webtoon --kind image")
        print("  python3 -m src.main gems show-prompt news --kind video")
        return 0

    if action == "show-prompt":
        key = args.key
        kind = args.kind
        try:
            gem_cfg = get_gem_config(kind, key)
        except GemNotFoundError as e:
            print(f"\n❌ {e}", file=sys.stderr)
            return 1

        gem_name = gem_cfg["gem_name"]
        prompt_file = gem_cfg.get("prompt_file", "")
        prompt_text = get_system_prompt_text(prompt_file) if prompt_file else "(지침 파일 미등록)"

        print(f"\n📋 Gem 지침: [{kind}/{key}]  {gem_name}")
        print("─" * 60)
        print("아래 내용을 복사하여 gemini.google.com/gems 에서")
        print(f"새 Gem 이름을 '{gem_name}' 으로 설정하고 지침란에 붙여넣으세요.")
        print("─" * 60)
        print()
        print(prompt_text)
        print()
        return 0

    print(f"❌ 알 수 없는 gems 액션: {action}", file=sys.stderr)
    return 1


def _download_celebrity_portrait_candidates(
    name: str, qualifier: str | None = None, count: int = 3,
) -> list[dict]:
    """[Legacy] 대표 이미지 3장 후보. 씬마다 다른 이미지를 원하면
    `_download_celebrity_scene_images`를 사용하세요.
    """
    try:
        from datetime import datetime
        from src.config.settings import DATA_DIR
        from src.illustrator.naver_image_search import (
            NaverImageSearcher, NaverImageSearchError,
        )
        portrait_dir = DATA_DIR / "celebrity_portraits"
        portrait_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]
        query = f"{name} {qualifier}".strip() if qualifier else name
        searcher = NaverImageSearcher()
        results = searcher.search(query, count=count)
        saved = searcher.download(
            results, portrait_dir, filename_prefix=f"{safe_name}_{timestamp}",
        )
        return [
            {"path": str(p), "filename": p.name}
            for p in saved
        ]
    except Exception as exc:
        logger.warning("인물 이미지 후보 다운로드 실패: %s", exc)
        return []


def _download_celebrity_scene_images(
    name: str, script, qualifier: str | None = None,
) -> list[dict]:
    """Phase 1에서 각 씬마다 1장씩 이미지 다운로드 (사용자 요청 2026-04-21 v3).

    씬의 image_query가 있으면 그 쿼리 사용. 인물명 단독이면 qualifier 결합.
    동일 쿼리는 API 1회 호출 후 결과를 씬 수만큼 분배 (쿼터 절약).

    Returns [{"scene_id": N, "path": "...", "filename": "...", "query": "..."}, ...]
    """
    try:
        from datetime import datetime
        from src.config.settings import DATA_DIR
        from src.illustrator.naver_image_search import (
            NaverImageSearcher, NaverImageSearchError,
        )
    except Exception as exc:
        logger.warning("이미지 검색 의존성 로드 실패: %s", exc)
        return []

    portrait_dir = DATA_DIR / "celebrity_portraits"
    portrait_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)[:30]

    searcher = NaverImageSearcher()
    results: list[dict] = []
    query_cache: dict[str, list] = {}
    query_cursor: dict[str, int] = {}

    for scene in script.scenes:
        base_query = (scene.image_query or "").strip() or name
        # 인물명 단독 쿼리면 qualifier 결합 (동명이인 방지)
        query = (
            f"{name} {qualifier}".strip()
            if qualifier and base_query == name
            else base_query
        )
        try:
            if query not in query_cache:
                search_res = searcher.search(query, count=3)
                safe_q = "".join(c if c.isalnum() else "_" for c in query)[:25] or "q"
                saved = searcher.download(
                    search_res, portrait_dir,
                    filename_prefix=f"{safe_name}_{timestamp}_s{scene.id:02d}_{safe_q}",
                )
                query_cache[query] = list(saved)
                query_cursor[query] = 0
            cache = query_cache[query]
            if not cache:
                logger.warning("씬 %d: '%s' 결과 0건", scene.id, query)
                continue
            idx = query_cursor[query]
            path = cache[idx % len(cache)]
            query_cursor[query] = idx + 1
            results.append({
                "scene_id": scene.id,
                "path": str(path),
                "filename": path.name,
                "query": query,
            })
        except Exception as exc:  # NaverImageSearchError 포함
            logger.warning("씬 %d '%s' 이미지 실패: %s", scene.id, query, exc)
            continue

    return results


if __name__ == "__main__":
    sys.exit(main())
