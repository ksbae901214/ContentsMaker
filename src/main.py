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
        code, _, _ = _run_tts(script)
        return code

    except Exception as e:
        logger.error("TTS 오류: %s", e)
        print(f"\n❌ TTS 오류: {e}", file=sys.stderr)
        return 1


def _run_tts(script):
    """Run TTS generation with per-scene timing.

    Returns (exit_code, voice_path, scene_timings).
    scene_timings is a list of {scene_id, start_ms, end_ms} dicts for
    precise audio-to-scene synchronization.
    """
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
            info = scraper.fetch_person(name)  # 캐시 히트 → 네트워크 요청 안 함
        else:
            # Step 1: Namuwiki fetch
            print(f"📚 Step 1/6: 나무위키에서 '{name}' 정보 조회 중...")
            scraper = NamuwikiScraper()
            info = scraper.fetch_person(name)
            print(f"   요약: {info.summary[:60]}")
            print(f"   경력 {len(info.career_highlights)}건 / 여담 {len(info.trivia)}건")

            # Step 2: Script generation
            print("📝 Step 2/6: 대본 생성 중...")
            script, script_path = analyze_celebrity(info)
            print(
                f"   감정: {script.metadata.emotion_type} | "
                f"씬: {len(script.scenes)}개 | "
                f"길이: {script.metadata.duration}초"
            )
            print(f"   저장: {script_path}")

        # ── --analyze-only: Phase 1 종료 ──
        if analyze_only:
            payload = {
                "script_path": str(script_path),
                "name": name,
                "title": script.metadata.title,
                "emotion": script.metadata.emotion_type,
                "duration": script.metadata.duration,
                "scene_count": len(script.scenes),
                "source_url": info.source_url,
            }
            # 마지막 줄이 JSON 결과 — route.ts가 파싱
            print("ANALYZE_DONE " + _json.dumps(payload, ensure_ascii=False))
            return 0

        # Step 3: Images (Naver) — optional
        image_paths: list[dict] | None = None
        if not getattr(args, "no_images", False):
            image_paths = _run_celebrity_images(name, script)

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
        )
        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ 완료! '{name}' 소개 쇼츠 생성")
        print(f"   영상: {output_path}")
        print(f"   크기: {file_size_mb:.1f} MB")
        print(f"   출처: {info.source_url}")
        print("   ℹ️  학습 목적 전용 — 공개 업로드 전 초상권/저작권 확인 필요")
        return 0

    except (NamuwikiScraperError, AnalyzerError, RenderError) as e:
        logger.error("유명인 파이프라인 오류: %s", e)
        print(f"\n❌ 오류: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n취소되었습니다.")
        return 130


def _run_celebrity_images(name: str, script) -> list[dict] | None:
    """씬별 image_query 에 따라 네이버 이미지 검색 + 다운로드.

    Phase 9 v2 (2026-04-21): 씬마다 다른 쿼리 지원. "서울대를 졸업했다" 씬이면
    scene.image_query="서울대학교 정문"으로 검색해 해당 이미지를 받는다.
    None이면 인물명으로 폴백. 동일 쿼리는 한 번만 API 호출 후 재사용.

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
        "tts", help="스크립트 → 음성 변환 (edge-tts)"
    )
    tts_parser.add_argument("--file", "-f", type=str, required=True, help="script.json 경로")

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
