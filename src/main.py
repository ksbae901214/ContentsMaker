"""ContentsMaker CLI - Blind post to Shorts pipeline.

Usage:
    python3 -m src.main manual --file <path>
    python3 -m src.main manual --interactive
    python3 -m src.main analyze --file <raw.json> [--with-tts]
    python3 -m src.main tts --file <script.json>
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
        script = analyze(post)

        print(f"\n✅ 스크립트 생성 완료")
        print(f"   제목: {script.metadata.title}")
        print(f"   감정: {script.metadata.emotion_type}")
        print(f"   씬 수: {len(script.scenes)}")
        print(f"   길이: {script.metadata.duration}초")

        if args.with_tts:
            return _run_tts(script)

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
        return _run_tts(script)

    except Exception as e:
        logger.error("TTS 오류: %s", e)
        print(f"\n❌ TTS 오류: {e}", file=sys.stderr)
        return 1


def _run_tts(script) -> int:
    """Run TTS generation on a ShortsScript."""
    from src.tts.edge_tts_generator import TTSError, generate_voice

    try:
        logger.info("TTS 생성 시작...")
        voice_path = generate_voice(script)
        file_size_kb = voice_path.stat().st_size / 1024

        print(f"\n✅ 음성 생성 완료")
        print(f"   파일: {voice_path}")
        print(f"   크기: {file_size_kb:.1f} KB")
        print(f"   음성: {script.audio.voice}")
        return 0

    except TTSError as e:
        logger.error("TTS 오류: %s", e)
        print(f"\n❌ TTS 오류: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="contentsmaker",
        description="블라인드 인기글 → 쇼츠 영상 자동 생성 파이프라인",
    )
    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

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

    # crawl subcommand (P2 placeholder)
    subparsers.add_parser("crawl", help="블라인드 URL 자동 크롤링 (미구현)")

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "manual": cmd_manual,
        "analyze": cmd_analyze,
        "tts": cmd_tts,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    if args.command == "crawl":
        print("⚠️  자동 크롤링은 아직 구현되지 않았습니다")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
