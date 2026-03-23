"""ContentsMaker CLI - Blind post to Shorts pipeline.

Usage:
    python3 src/main.py manual --file <path>        # Load from JSON file
    python3 src/main.py manual --interactive         # Interactive input
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
    manual_group.add_argument(
        "--file", "-f", type=str, help="JSON 파일 경로"
    )
    manual_group.add_argument(
        "--interactive", "-i", action="store_true", help="대화형 입력 모드"
    )

    # crawl subcommand (P2 placeholder)
    crawl_parser = subparsers.add_parser(
        "crawl", help="블라인드 URL 자동 크롤링 (P2)"
    )
    crawl_parser.add_argument(
        "--url", "-u", type=str, help="블라인드 게시글 URL"
    )

    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "manual":
        return cmd_manual(args)

    if args.command == "crawl":
        print("⚠️  자동 크롤링은 아직 구현되지 않았습니다 (Phase 2)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
