"""편성 비중 추적 (040) — 중앙값이 높은 카테고리를 편성으로 끌어올린다.

**측정 배경**: 2026-09-04 스냅샷 133편을 036 카테고리로 갈랐을 때

| 카테고리 | 편수 | 비중 | 조회수 중앙 |
|---|---|---|---|
| political | 88 | 66% | 1,200 |
| 인물 논란(원장 미기록) | 23 | 17% | **2,200** |
| economic | 14 | 11% | 1,150 |
| society | 8 | 6% | **1,912** |

중앙값이 높은 두 카테고리가 편성의 6~17%뿐이라 **채널 중앙값이 정치에 끌려간다.**
036 리포트도 이미 society 확대를 경고하고 있었다(147%). 이 모듈은 그 경고를
리포트가 아니라 **렌더 시점**으로 옮긴다 — 편성은 사후에 알면 늦다.

**목표 비중**: 사용자 확정(2026-09-04). 범죄 소재는 제외한다.

- political 40% — 축소하되 유지 (채널 정체성)
- society 25% — 실측 중앙 1,912, 확대 1순위
- entertainment 20% — 인물 논란(박위·박수홍 계열). **범죄 아님**
- economic 15% — 유지

**판정 근거**: 036 카테고리 원장(`category_ledger.json`)의 `recorded_at` 순.
유튜브 쪽에는 카테고리가 안 남으므로 로컬 원장이 유일한 소스다.

**정책**: 경고, 차단 없음. 표본이 `MIN_SAMPLE` 미만이면 침묵한다 — 원장이 이제
막 쌓이기 시작한 단계라 적은 표본으로 경고하면 노이즈만 된다.
우회: `"balance_gate": "off"`.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.shorts_category import CATEGORIES

GATE_KEY = "balance_gate"
GATE_OFF = "off"

WINDOW = 20          # 최근 N편으로 비중을 잰다
MIN_SAMPLE = 8       # 이하 표본은 판단 보류
TOLERANCE = 0.10     # 목표 대비 ±10%p 를 넘으면 경고

# 사용자 확정 편성 목표 (2026-09-04)
TARGET_MIX: dict[str, float] = {
    "political": 0.40,
    "society": 0.25,
    "entertainment": 0.20,
    "economic": 0.15,
}

CATEGORY_LABELS: dict[str, str] = {
    "political": "정치",
    "society": "사회",
    "entertainment": "인물 논란(연예·사회)",
    "economic": "경제",
}

DEFAULT_LEDGER_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "channel_analytics" / "category_ledger.json"
)


def load_recent_categories(path: Path, window: int = WINDOW) -> tuple[str, ...]:
    """원장에서 최근 `window` 편의 카테고리를 최신순으로. 없거나 깨졌으면 빈 튜플.

    계측 보조 장치이므로 파일이 손상돼도 렌더를 막지 않는다 (036 `load_ledger`
    와 같은 방침).
    """
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        return ()
    rows = [
        (entry.get("recorded_at", ""), entry["category"])
        for entry in entries.values()
        if isinstance(entry, dict) and entry.get("category") in CATEGORIES
    ]
    rows.sort(key=lambda r: r[0], reverse=True)
    return tuple(cat for _, cat in rows[:window])


def mix_of(categories: tuple[str, ...]) -> dict[str, float]:
    """카테고리 시퀀스 → {카테고리: 비중}. 빈 입력은 빈 dict."""
    total = len(categories)
    if not total:
        return {}
    return {cat: n / total for cat, n in Counter(categories).items()}


def over_target(mix: dict[str, float]) -> tuple[str, ...]:
    """목표 + 허용치를 넘은 카테고리."""
    return tuple(
        cat for cat, share in sorted(mix.items())
        if share > TARGET_MIX.get(cat, 0.0) + TOLERANCE
    )


def under_target(mix: dict[str, float]) -> tuple[str, ...]:
    """목표 - 허용치에 못 미치는 카테고리 (부족분이 큰 순)."""
    gaps = {
        cat: target - mix.get(cat, 0.0)
        for cat, target in TARGET_MIX.items()
        if mix.get(cat, 0.0) < target - TOLERANCE
    }
    return tuple(sorted(gaps, key=lambda c: -gaps[c]))


def _pct(share: float) -> str:
    return f"{share * 100:.0f}%"


def mix_report_lines(categories: tuple[str, ...]) -> list[str]:
    """목표 대비 현재 비중을 사람이 읽을 수 있게."""
    mix = mix_of(categories)
    lines = []
    for cat, target in TARGET_MIX.items():
        share = mix.get(cat, 0.0)
        mark = "!" if abs(share - target) > TOLERANCE else " "
        lines.append(
            f"{mark} {cat:<14} {_pct(share):>4} / 목표 {_pct(target):>4} "
            f"({CATEGORY_LABELS[cat]})")
    return lines


def balance_warnings(cfg: dict, ledger_path: Path | None = None) -> list[str]:
    """이 편의 카테고리가 이미 과대 편성인지 경고 (하드 오류 아님).

    우회: `"balance_gate": "off"`.
    """
    if cfg.get(GATE_KEY) == GATE_OFF:
        return []
    from scripts.shorts_category import resolve_config_category

    recent = load_recent_categories(ledger_path or DEFAULT_LEDGER_PATH)
    if len(recent) < MIN_SAMPLE:
        return []

    category = resolve_config_category(cfg)
    mix = mix_of(recent)
    if category not in over_target(mix):
        return []

    share = mix.get(category, 0.0)
    target = TARGET_MIX.get(category, 0.0)
    alternatives = under_target(mix)
    alt = ", ".join(
        f"{c}({CATEGORY_LABELS[c]})" for c in alternatives[:2]) or "없음"
    return [
        f"[040] 편성 비중 초과 — 최근 {len(recent)}편 중 {category}가 "
        f"{_pct(share)}, 목표 {_pct(target)}. 이 편도 {category}입니다. "
        f"실측 중앙값은 society 1,912 / 인물 논란 2,200 vs political 1,200이라 "
        f"정치 과편성이 채널 중앙값을 끌어내립니다. 부족한 축: {alt}"
    ]


__all__ = [
    "CATEGORY_LABELS", "DEFAULT_LEDGER_PATH", "GATE_KEY", "GATE_OFF",
    "MIN_SAMPLE", "TARGET_MIX", "TOLERANCE", "WINDOW", "balance_warnings",
    "load_recent_categories", "mix_of", "mix_report_lines", "over_target",
    "under_target",
]
