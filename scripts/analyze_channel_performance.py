"""채널 쇼츠 성과 피드백 CLI (prompt_plan 031 Phase 3).

yt-dlp 로 내 채널 쇼츠의 조회수·제목·길이를 수집해 제목 유형(hook형/보도형)·
길이 구간별 상관 리포트를 만들고, JSON 스냅샷으로 회차 간 추세를 비교한다.
공개 데이터만 사용 — OAuth 불필요. (리텐션·스와이프율은 API 미제공 →
YouTube Studio 수동 확인 병행.)

사용:
  .venv311/bin/python scripts/analyze_channel_performance.py \
      [--channel UCYNNMfkMW_EZJBp514-DjaA] [--details 30] [--out data/channel_analytics]

  --details N : 최근 N편은 개별 조회로 upload_date 보강 (업로드 공백 분석용, 기본 30)
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_CHANNEL = "UCYNNMfkMW_EZJBp514-DjaA"
DEFAULT_OUT = Path("data/channel_analytics")
GAP_ALERT_DAYS = 3          # 030 실측: 업로드 공백 → 배포 붕괴

HOOK_MARKERS = (
    "참교육", "사이다", "직격", "저격", "응징", "역공", "반격",
    "발끈", "폭발", "일침", "일갈", "돌직구",
)
REPORT_SUFFIXES = (
    "설명", "밝혔다", "밝혔습니다", "논의", "제시", "요구", "촉구",
    "발표", "가중", "수용", "예정", "전망",
)


# ── 순수 분석 로직 (테스트 대상) ────────────────────────────────────
def classify_title(title: str) -> str:
    """030 벤치마크 기준 제목 분류: hook형 / 보도형(report) / 중립."""
    t = title.strip()
    if not t:
        return "neutral"
    if ("?" in t or t.endswith(("…", "...")) or any(q in t for q in ('"', "“", "'"))
            or any(m in t for m in HOOK_MARKERS)):
        return "hook"
    if any(t.rstrip(".…").endswith(s) for s in REPORT_SUFFIXES):
        return "report"
    return "neutral"


def duration_bucket(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "unknown"
    if seconds < 30:
        return "<30s"
    if seconds < 45:
        return "30-45s"
    if seconds <= 60:
        return "45-60s"
    return "60s+"


def _median_views(entries: list[dict]) -> int:
    views = [e["view_count"] for e in entries if e.get("view_count") is not None]
    return int(statistics.median(views)) if views else 0


def summarize(entries: list[dict]) -> dict:
    """전체/제목유형별/길이구간별 조회수 요약 + 상·하위 5편."""
    valid = [e for e in entries if e.get("view_count") is not None]
    by_type: dict[str, list[dict]] = {}
    by_bucket: dict[str, list[dict]] = {}
    for e in valid:
        by_type.setdefault(classify_title(e.get("title", "")), []).append(e)
        by_bucket.setdefault(duration_bucket(e.get("duration")), []).append(e)
    ranked = sorted(valid, key=lambda e: e["view_count"], reverse=True)
    return {
        "count": len(valid),
        "median_views": _median_views(valid),
        "by_title_type": {
            k: {"count": len(v), "median_views": _median_views(v)}
            for k, v in sorted(by_type.items())
        },
        "by_duration": {
            k: {"count": len(v), "median_views": _median_views(v)}
            for k, v in sorted(by_bucket.items())
        },
        "top5": [_brief(e) for e in ranked[:5]],
        "bottom5": [_brief(e) for e in ranked[-5:]][::-1],
    }


def _brief(e: dict) -> dict:
    return {"id": e.get("id", ""), "title": e.get("title", ""),
            "view_count": e.get("view_count", 0)}


def upload_gaps(dates: list[str], alert_days: int = GAP_ALERT_DAYS) -> list[dict]:
    """upload_date(YYYYMMDD) 목록에서 alert_days 초과 공백 구간 검출."""
    parsed = sorted({datetime.strptime(d, "%Y%m%d") for d in dates if d})
    gaps = []
    for prev, cur in zip(parsed, parsed[1:]):
        gap = (cur - prev).days
        if gap > alert_days:
            gaps.append({"from": prev.strftime("%Y-%m-%d"),
                         "to": cur.strftime("%Y-%m-%d"), "gap_days": gap})
    return gaps


def compare_snapshots(prev: list[dict], cur: list[dict], top_n: int = 10) -> list[dict]:
    """스냅샷 간 편별 조회수 증가분 상위 top_n (신규 편 포함)."""
    prev_map = {e["id"]: e.get("view_count") or 0 for e in prev if e.get("id")}
    deltas = []
    for e in cur:
        vid = e.get("id")
        if not vid or e.get("view_count") is None:
            continue
        delta = e["view_count"] - prev_map.get(vid, 0)
        if delta > 0:
            deltas.append({**_brief(e), "delta": delta, "new": vid not in prev_map})
    return sorted(deltas, key=lambda d: d["delta"], reverse=True)[:top_n]


def build_report_md(channel: str, summary: dict, gaps: list[dict],
                    deltas: list[dict], generated_at: str) -> str:
    lines = [
        f"# 채널 쇼츠 성과 리포트 — {generated_at}",
        "",
        f"채널: `{channel}` / 분석 대상 {summary['count']}편 / "
        f"**전체 중앙값 {summary['median_views']:,}회**",
        "",
        "## 제목 유형별 (hook형 vs 보도형)",
        "",
        "| 유형 | 편수 | 조회수 중앙값 |",
        "|---|---|---|",
    ]
    for k, v in summary["by_title_type"].items():
        lines.append(f"| {k} | {v['count']} | {v['median_views']:,} |")
    lines += ["", "## 길이 구간별", "", "| 구간 | 편수 | 조회수 중앙값 |", "|---|---|---|"]
    for k, v in summary["by_duration"].items():
        lines.append(f"| {k} | {v['count']} | {v['median_views']:,} |")
    lines += ["", "## 상위 5편"]
    lines.extend(f"- {e['view_count']:,}회 — {e['title']}" for e in summary["top5"])
    lines += ["", "## 하위 5편"]
    lines.extend(f"- {e['view_count']:,}회 — {e['title']}" for e in summary["bottom5"])
    if gaps:
        lines += ["", f"## ⚠️ 업로드 공백 ({GAP_ALERT_DAYS}일 초과 — 배포 붕괴 위험)"]
        lines.extend(f"- {g['from']} → {g['to']} ({g['gap_days']}일)" for g in gaps)
    if deltas:
        lines += ["", "## 직전 스냅샷 대비 조회수 증가 상위"]
        lines.extend(
            f"- +{d['delta']:,} {'(신규) ' if d['new'] else ''}— {d['title']}"
            for d in deltas
        )
    lines += ["", "---", "리텐션·스와이프율은 YouTube Studio에서 수동 확인 필요.", ""]
    return "\n".join(lines)


# ── 수집 (yt-dlp) ──────────────────────────────────────────────────
def collect_flat(channel: str) -> list[dict]:
    """쇼츠 탭 flat-playlist 1회 조회 — id/title/view_count(/duration)."""
    url = f"https://www.youtube.com/channel/{channel}/shorts"
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", url, "--flat-playlist", "-J",
         "--no-warnings"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp flat-playlist 실패: {r.stderr[:300]}")
    data = json.loads(r.stdout)
    return [
        {"id": e.get("id"), "title": e.get("title") or "",
         "view_count": e.get("view_count"), "duration": e.get("duration"),
         "upload_date": e.get("upload_date")}
        for e in (data.get("entries") or []) if e
    ]


def enrich_details(entries: list[dict], n: int) -> list[dict]:
    """최근 n편 개별 조회로 upload_date·duration 보강 (편당 ~1-2초 소요)."""
    out = []
    for i, e in enumerate(entries):
        if i >= n or (e.get("upload_date") and e.get("duration")):
            out.append(e)
            continue
        r = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "-J", "--no-warnings",
             f"https://www.youtube.com/watch?v={e['id']}"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            try:
                d = json.loads(r.stdout)
                e = {**e,
                     "upload_date": d.get("upload_date") or e.get("upload_date"),
                     "duration": d.get("duration") or e.get("duration"),
                     "view_count": d.get("view_count", e.get("view_count"))}
            except json.JSONDecodeError:
                pass
        out.append(e)
        print(f"   상세 {i+1}/{min(n, len(entries))}: {e.get('title', '')[:40]}", flush=True)
    return out


def load_latest_snapshot(out_dir: Path) -> list[dict]:
    snaps = sorted(out_dir.glob("*_snapshot.json"))
    if not snaps:
        return []
    return json.loads(snaps[-1].read_text(encoding="utf-8")).get("entries", [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--channel", default=DEFAULT_CHANNEL)
    ap.add_argument("--details", type=int, default=30)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"📡 채널 쇼츠 수집 중: {args.channel}", flush=True)
    entries = collect_flat(args.channel)
    print(f"✅ {len(entries)}편 수집", flush=True)
    if args.details > 0:
        print(f"🔍 최근 {args.details}편 상세 보강 중...", flush=True)
        entries = enrich_details(entries, args.details)

    prev = load_latest_snapshot(args.out)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = args.out / f"{stamp}_snapshot.json"
    snapshot.write_text(
        json.dumps({"channel": args.channel, "collected_at": stamp,
                    "entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = summarize(entries)
    gaps = upload_gaps([e.get("upload_date") or "" for e in entries])
    deltas = compare_snapshots(prev, entries) if prev else []
    report = args.out / f"{stamp}_report.md"
    report.write_text(
        build_report_md(args.channel, summary, gaps, deltas,
                        datetime.now().strftime("%Y-%m-%d %H:%M")),
        encoding="utf-8",
    )
    print(f"\n📊 전체 중앙값 {summary['median_views']:,}회 ({summary['count']}편)")
    for k, v in summary["by_title_type"].items():
        print(f"   {k:8s}: {v['count']:3d}편, 중앙값 {v['median_views']:,}회")
    print(f"\n📁 리포트: {report}\n📁 스냅샷: {snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
