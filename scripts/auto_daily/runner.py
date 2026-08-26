"""039 Phase 5 — 슬롯 오케스트레이션 (소재 → 컷 → 초안 → 렌더 → 판정 → 게시).

    PYTHONPATH=. .venv311/bin/python -m scripts.auto_daily.runner --slot morning

**설계 원칙은 실패 격리다.** 한 소재가 실패하면 다음 소재로, 한 후보 영상에서
컷을 못 뽑으면 다음 후보로 넘어간다. 어느 단계가 죽어도 예외를 위로 던지지 않고
사유를 모아 알림에 싣는다 — 아침 슬롯이 죽었다고 점심·저녁까지 날아가면 안 된다.

바깥 세계(네이버·yt-dlp·Claude·Remotion·업로드)는 `Deps` 로 주입한다.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from scripts.auto_daily.cut_planner import build_cuts, fetch_auto_subs, parse_word_timestamps
from scripts.auto_daily.notify import build_summary, notify
from scripts.auto_daily.review_gate import GatePolicy, decide, load_gate_policy
from scripts.auto_daily.slots import (
    AUTO_DAILY_ROOT, KST, SLOT_NAMES, SlotSpec, slot_for_name, work_dir_for,
)
from scripts.auto_daily.topic_ranker import TopicCluster

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "config.json"
HOOK_MAX_SEC = 10.0          # V2.1/V2.2 훅 상한 — scene 0 은 이 안에서 끝나야 한다
BODY_MAX_SEC = 12.0


@dataclass(frozen=True)
class SlotResult:
    slot: str
    status: str                  # published | held | failed | skipped
    reasons: tuple[str, ...]
    config: dict | None
    video: Path | None
    work_dir: Path


@dataclass(frozen=True)
class Deps:
    """바깥 세계와 닿는 지점. 테스트·부분 재실행에서 갈아끼운다."""

    collect_topics: object
    find_candidates: object
    plan_cuts: object
    draft: object
    render: object
    chat_block: object
    publish: object
    notifier: object
    gate_policy: GatePolicy = field(default_factory=load_gate_policy)


# ── 락 ──────────────────────────────────────────────────────────────
@contextmanager
def slot_lock(slot_name: str, *, root: Path | None = None):
    """슬롯 중복 실행 방지. 이미 잡혀 있으면 False 를 내주고 아무것도 안 한다."""
    base = Path(root) if root is not None else AUTO_DAILY_ROOT
    base.mkdir(parents=True, exist_ok=True)
    path = base / f".{slot_name}.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield True
    finally:
        # 예외가 나도 반드시 푼다 — 안 그러면 다음 날까지 슬롯이 막힌다.
        path.unlink(missing_ok=True)


# ── 기본 구현 ───────────────────────────────────────────────────────
def _default_collect(slot: SlotSpec, now: datetime) -> list[TopicCluster]:
    from scripts.auto_daily.topic_collector import collect_topics
    return collect_topics(slot, now)


def _default_find_candidates(slot: SlotSpec, topic: TopicCluster):
    from scripts.auto_daily.source_finder import (
        load_policy, pick_candidates, search_candidates,
    )
    return pick_candidates(search_candidates(topic.headline), load_policy())


def _default_plan_cuts(candidate, work_dir: Path, key: str):
    """자동자막 → 단어 타임스탬프 → 문장 경계 컷 후보 (037-2)."""
    vtt = fetch_auto_subs(candidate.url, Path(work_dir) / "_sub", key)
    if vtt is None:
        return []
    words = parse_word_timestamps(vtt.read_text(encoding="utf-8"))
    return build_cuts(words, min_sec=1.0, max_sec=BODY_MAX_SEC)


def _default_draft(topic, candidate, cuts, category, slug):
    from scripts.auto_daily.config_drafter import draft_with_gates
    return draft_with_gates(topic, candidate, cuts, category=category, slug=slug)


def _default_render(config_path: Path, work_dir: Path,
                    *, runner=subprocess.run) -> Path | None:
    """기존 V2.2 렌더러를 그대로 부른다 — 렌더 파이프라인은 손대지 않는다.

    **산출물은 `work_dir` 이 아니라 `data/political_pro/{slug}/` 에 생긴다.**
    렌더러가 마지막 stdout 줄에 mp4 경로를 찍으므로 그 줄을 읽는다 (경로 규칙을
    여기 복제하면 렌더러가 바뀔 때 조용히 어긋난다).
    """
    from src.config.settings import PROJECT_ROOT

    script = "scripts/render_political_v2_2.py"
    last_stdout = ""
    for stage in ("download", "render"):
        result = runner(
            [sys.executable, script, str(config_path), stage],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        )
        if getattr(result, "returncode", 1) != 0:
            logger.error("렌더 %s 실패: %s", stage, (result.stderr or "")[-500:])
            return None
        last_stdout = result.stdout or ""

    return _mp4_from_stdout(last_stdout)


def _mp4_from_stdout(stdout: str) -> Path | None:
    for line in reversed((stdout or "").splitlines()):
        candidate = Path(line.strip())
        if candidate.suffix == ".mp4" and candidate.exists():
            return candidate
    return None


def _default_chat_block(cfg: dict) -> str:
    from scripts.political_upload_package import build_chat_ready_block
    return build_chat_ready_block(cfg)


def _default_publish(video: Path, cfg: dict, slug: str):
    from scripts.auto_daily.upload_shorts import metadata_from_config, publish
    return publish(video, metadata_from_config(cfg),
                   log_path=AUTO_DAILY_ROOT / "publish_log.jsonl", slug=slug)


def default_deps() -> Deps:
    return Deps(
        collect_topics=_default_collect,
        find_candidates=_default_find_candidates,
        plan_cuts=_default_plan_cuts,
        draft=_default_draft,
        render=_default_render,
        chat_block=_default_chat_block,
        publish=_default_publish,
        notifier=lambda title, message, reveal=None: notify(
            title, message, reveal=reveal),
    )


# ── 파이프라인 ──────────────────────────────────────────────────────
def _slug_for(slot: SlotSpec, topic: TopicCluster, now: datetime) -> str:
    anchor = "".join(ch for ch in topic.anchor if ch.isalnum())[:12] or slot.name
    return f"{now:%Y%m%d}_{anchor}_v2_2"


def _draft_any(slot: SlotSpec, topics, now: datetime, work_dir: Path, deps: Deps):
    """소재 × 후보영상을 돌며 게이트를 통과하는 첫 초안을 찾는다."""
    reasons: list[str] = []
    for topic in topics:
        candidates = deps.find_candidates(slot, topic)
        if not candidates:
            reasons.append(f"'{topic.anchor}': 허용 채널 후보 없음 (037-3 화이트리스트)")
            continue
        for candidate in candidates:
            cuts = deps.plan_cuts(candidate, work_dir, candidate.video_id)
            if not cuts:
                reasons.append(f"'{candidate.title}': 말 끝맺음 컷을 뽑지 못함")
                continue
            slug = _slug_for(slot, topic, now)
            result = deps.draft(topic, candidate, cuts, slot.category, slug)
            if result.ok:
                return result, candidate, reasons
            reasons.append(f"'{topic.anchor}': 초안 게이트 실패 — "
                           + " / ".join(result.errors[:2]))
    return None, None, reasons


def _finish(slot: SlotSpec, status: str, reasons: list[str], work_dir: Path,
            deps: Deps, *, config=None, video=None, chat="",
            decision=None, outcome=None) -> SlotResult:
    """알림을 보내고 결과를 돌려준다. 모든 종료 경로가 여기를 지난다."""
    from scripts.auto_daily.review_gate import Decision
    decision = decision or Decision(status == "published", tuple(reasons))
    summary = build_summary(
        slot=slot.name, decision=decision, video=video, chat_block=chat,
        youtube_url=getattr(outcome, "youtube_url", None),
        tiktok_publish_id=getattr(outcome, "tiktok_publish_id", None),
        comment_posted=bool(getattr(outcome, "comment_id", None)),
        errors=tuple(reasons) if status == "failed" else (),
    )
    try:
        deps.notifier(f"ContentsMaker — {slot.name}", summary, reveal=video)
    except Exception as exc:  # noqa: BLE001 — 알림 실패로 슬롯을 죽이지 않는다
        logger.warning("알림 실패: %s", exc)
    logger.info("[%s] %s\n%s", slot.name, status, summary)
    return SlotResult(slot=slot.name, status=status, reasons=tuple(reasons),
                      config=config, video=video, work_dir=work_dir)


def run_slot(slot_name: str, *, now: datetime | None = None,
             root: Path | None = None, deps: Deps | None = None) -> SlotResult:
    """슬롯 하나를 끝까지 실행한다. 예외를 위로 던지지 않는다(슬롯 이름 오류 제외)."""
    slot = slot_for_name(slot_name)
    now = now or datetime.now(KST)
    deps = deps or default_deps()
    work_dir = work_dir_for(slot, now, root=root)

    with slot_lock(slot_name, root=root) as acquired:
        if not acquired:
            logger.warning("[%s] 이미 실행 중 — 건너뛴다", slot_name)
            return SlotResult(slot_name, "skipped", ("이미 실행 중",), None, None,
                              work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        return _run(slot, now, work_dir, deps)


def _run(slot: SlotSpec, now: datetime, work_dir: Path, deps: Deps) -> SlotResult:
    from scripts.auto_daily.topic_collector import write_topics

    topics = deps.collect_topics(slot, now)
    write_topics(slot, list(topics), work_dir, now=now)
    if not topics:
        return _finish(slot, "failed", ["소재 후보를 찾지 못했습니다"], work_dir, deps)

    draft, candidate, reasons = _draft_any(slot, topics, now, work_dir, deps)
    if draft is None:
        return _finish(slot, "failed", reasons or ["초안 작성 실패"], work_dir, deps)

    config_path = work_dir / CONFIG_FILENAME
    config_path.write_text(json.dumps(draft.config, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    video = deps.render(config_path, work_dir)
    if video is None:
        return _finish(slot, "failed", [*reasons, "렌더 실패 — 로그를 확인하세요"],
                       work_dir, deps, config=draft.config)

    chat = deps.chat_block(draft.config)
    decision = decide(draft.config, warnings=tuple(draft.warnings),
                      policy=deps.gate_policy,
                      channel_registered=candidate is not None)
    if not decision.should_publish:
        return _finish(slot, "held", list(decision.reasons), work_dir, deps,
                       config=draft.config, video=video, chat=chat,
                       decision=decision)

    try:
        outcome = deps.publish(video, draft.config, draft.config.get("slug", ""))
    except Exception as exc:  # noqa: BLE001 — 업로드 실패도 사유로 남긴다
        return _finish(slot, "failed", [f"업로드 실패: {exc}"], work_dir, deps,
                       config=draft.config, video=video, chat=chat)

    return _finish(slot, "published", list(outcome.errors), work_dir, deps,
                   config=draft.config, video=video, chat=chat,
                   decision=decision, outcome=outcome)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="039 하루 3편 자동 제작 슬롯 실행")
    parser.add_argument("--slot", required=True, choices=SLOT_NAMES)
    parser.add_argument("--root", default=None, help="산출물 루트 (기본 data/auto_daily)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    result = run_slot(args.slot, root=Path(args.root) if args.root else None)
    print(f"[{result.slot}] {result.status}")
    for reason in result.reasons:
        print(f"  - {reason}")
    return 0 if result.status in ("published", "held") else 1


if __name__ == "__main__":
    raise SystemExit(main())
