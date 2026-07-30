"""정치쇼츠 V2.1 업로드 패키지 생성 (prompt_plan 031 Phase 2).

렌더 완료 시 `upload_package.md` 를 만들어 유튜브 업로드에 필요한 준비물을
한 파일로 모은다: 제목(A/B)·설명·해시태그·고정댓글·권장 업로드 시각·썸네일 후보.

FR-020(자동 업로드 차단)은 유지 — 이 모듈은 "복붙 준비물"만 생성한다.
"""
from __future__ import annotations

import re
import subprocess
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

TITLE_MIN, TITLE_MAX = 15, 30          # 030 벤치마크: 훅 제목 15~30자
MAX_HASHTAGS = 4                        # #인물명 2~4개 권장
UPLOAD_HOUR = 20                        # 평일 20~21시 직후 업로드 권장
DEFAULT_PINNED_COMMENT = "여러분 생각은 어떠신가요? 댓글로 남겨주세요 👇"

# 034 채널 분석: 제목 내 해시태그·보도체가 조회수 병목 (경쟁 채널 실측 —
# 12~20자 감정훅 + 해시태그 0~3개 vs 국회직캠 보도체 + 8~11개).
TITLE_HASHTAG_RE = re.compile(r"#\S+")
# 보도체 어미: ~한다/~합니다류 현재형 + 받침 ㅆ 과거형(했다/외쳤다/밝혔다…)
_REPORT_PLAIN_ENDINGS = ("한다", "합니다", "습니다", "입니다", "이다", "된다", "됐다")
_REPORT_PAST_RE = re.compile(r"[았었였졌쳤렸꼈혔웠했]다$")
_REPORT_WORDS = ("논란", "현황", "총정리", "공방", "설명", "촉구", "발표")


# ── 순수 로직 (테스트 대상) ─────────────────────────────────────────
def sanitize_yt_title(title: str) -> tuple[str, list[str]]:
    """제목에서 해시태그를 떼어 (정리된 제목, 추출 태그) 반환 — 설명란 이동용.

    유튜브·yt-dlp 경유 제목은 NFD(자모 분해형)일 수 있어 NFC 정규화 선행.
    """
    title = unicodedata.normalize("NFC", title)
    tags = TITLE_HASHTAG_RE.findall(title)
    clean = re.sub(r"\s{2,}", " ", TITLE_HASHTAG_RE.sub("", title)).strip()
    return clean, tags


def is_report_style(title: str) -> bool:
    """보도체 제목 감지 — 해시태그 제외 후 어미·단어 시그널 확인."""
    clean, _ = sanitize_yt_title(title)
    t = clean.rstrip(".…?!\"'")
    if not t:
        return False
    if any(w in t for w in _REPORT_WORDS):
        return True
    return t.endswith(_REPORT_PLAIN_ENDINGS) or bool(_REPORT_PAST_RE.search(t))


def gate_yt_title(cfg: dict) -> None:
    """yt_title 차단 게이트 (034) — 렌더·다운로드 전에 fail-fast.

    해시태그 포함·보도체 제목이면 ValueError. `"yt_title_lint": "off"` 로 우회.
    """
    if cfg.get("yt_title_lint") == "off":
        return
    yt = cfg.get("yt_title")
    if not yt:
        return
    if TITLE_HASHTAG_RE.search(yt):
        raise ValueError(
            "yt_title에 해시태그 포함 — 해시태그는 설명란으로 이동하세요 "
            "(우회: \"yt_title_lint\": \"off\")")
    if is_report_style(yt):
        raise ValueError(
            "yt_title이 보도체 — 감정훅/호기심형으로 수정하세요 "
            "(예: '눈물까지 고인 장동혁' / '아니 아직도 발급을 안 했어?') "
            "(우회: \"yt_title_lint\": \"off\")")


def lint_yt_title(title: str, persons: list[str] | None = None) -> list[str]:
    """030 제목 공식([악역]-[응징]-[주인공], 15~30자, 실명 포함) 점검 경고."""
    warnings = []
    n = len(title)
    if n < TITLE_MIN:
        warnings.append(f"제목 {n}자 — {TITLE_MIN}자 이상 권장 (구체성 부족)")
    elif n > TITLE_MAX:
        warnings.append(f"제목 {n}자 — {TITLE_MAX}자 이하 권장 (모바일 잘림)")
    if persons and not any(p in title for p in persons):
        warnings.append("제목에 실명(persons) 미포함 — 실명 1~2개 권장")
    if any(w in title for w in ("속보", "충격!")):
        warnings.append("'속보/충격!'형 제목은 실측상 천장이 낮음 — 서사형 권장")
    if TITLE_HASHTAG_RE.search(title):
        warnings.append("제목에 해시태그 포함 — 설명란으로 이동 "
                        "(쇼츠 피드 제목 잘림·스팸 인상, 034)")
    if is_report_style(title):
        warnings.append("보도체 제목 — 감정훅/호기심형 권장 (034 벤치마크)")
    return warnings


def build_hashtags(cfg: dict) -> list[str]:
    """config `hashtags` 우선, 없으면 `persons` 로 #인물명 자동 생성 (최대 4개)."""
    raw = cfg.get("hashtags") or [f"#{p}" for p in cfg.get("persons", [])]
    tags = [t if t.startswith("#") else f"#{t}" for t in raw]
    return tags[:MAX_HASHTAGS]


def suggest_upload_time(now: datetime) -> datetime:
    """다음 업로드 권장 시각: 가장 가까운 평일 20:00 (KST 로컬 기준)."""
    slot = now.replace(hour=UPLOAD_HOUR, minute=0, second=0, microsecond=0)
    if now.weekday() < 5 and now < slot:
        return slot
    nxt = slot + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def build_description(cfg: dict, hashtags: list[str]) -> str:
    head = cfg.get("description") or cfg.get("yt_title") or cfg["title"]
    parts = [sanitize_yt_title(head)[0]]
    ch, ti = cfg.get("source_channel", ""), cfg.get("source_title", "")
    if ch or ti:
        parts.append(f"출처: {ch}{' — ' if ch and ti else ''}{ti}")
    if cfg.get("youtube_url"):
        parts.append(cfg["youtube_url"])
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(parts)


def build_upload_package_md(
    cfg: dict,
    video_path: Path,
    suggested: datetime,
    thumbnails: list[Path] | None = None,
) -> str:
    yt_title_raw = cfg.get("yt_title") or cfg["title"]
    # 034: 제목의 해시태그는 자동으로 떼어 해시태그 섹션(설명란)으로 이동
    yt_title, extracted = sanitize_yt_title(yt_title_raw)
    hashtags = build_hashtags(cfg)
    for t in extracted:
        if t not in hashtags and len(hashtags) < MAX_HASHTAGS:
            hashtags.append(t)
    warnings = lint_yt_title(yt_title_raw, cfg.get("persons"))
    lines = [
        f"# 업로드 패키지 — {cfg['slug']}",
        "",
        f"**영상**: `{video_path}`",
        f"**권장 업로드 시각**: {suggested.strftime('%Y-%m-%d (%a) %H:%M')} "
        "— 평일 20~21시 직후, 일 1~3편 리듬 유지 (030 P0)",
        "",
        "## 제목 (A/B)",
        f"- A: {yt_title}",
    ]
    if cfg.get("yt_title_alt"):
        lines.append(f"- B: {cfg['yt_title_alt']}")
    else:
        lines.append("- (B안 미지정) ①감정훅형(예: '눈물까지 고인 장동혁') "
                     "②호기심형(예: '아니 아직도 발급을 안 했어?') 중 택1로 작성")
    if warnings:
        lines.append("")
        lines.extend(f"- ⚠️ {w}" for w in warnings)
    lines += [
        "",
        "## 설명",
        "```",
        build_description(cfg, hashtags),
        "```",
        "",
        "## 해시태그",
        " ".join(hashtags) if hashtags else "(persons 또는 hashtags 설정 필요)",
        "",
        "## 고정댓글",
        "```",
        cfg.get("pinned_comment") or DEFAULT_PINNED_COMMENT,
        "```",
    ]
    if thumbnails:
        lines += ["", "## 썸네일 후보"]
        lines.extend(f"- `{t}`" for t in thumbnails)
    lines += [
        "",
        "## 업로드 전 체크리스트 (034)",
        "- [ ] 썸네일 = 인물 표정 절정 컷인가 (웃음/한숨/야유/침묵 — 후보 중 선택)",
        "- [ ] 같은 주제 V2.1/V2.2 중복 업로드 금지 — 플랫폼 분리 (V2.2→유튜브, V2.1→틱톡)",
        "- [ ] 제목에 해시태그 없음 · 해시태그는 설명란 3~4개만",
        "",
        "---",
        "⚠️ 정치 콘텐츠 — 검수 후 **수동 업로드** (FR-020/021 자동 업로드 차단 유지).",
        "",
    ]
    return "\n".join(lines)


# ── 부수효과 (ffmpeg / 파일 쓰기) ──────────────────────────────────
def extract_thumbnail_candidates(
    video_path: Path, out_dir: Path, fracs: tuple[float, ...] = (0.02, 0.25, 0.55),
) -> list[Path]:
    """완성 영상에서 후보 프레임 추출 — 훅 초반·본문·클라이맥스 지점."""
    dur = _probe_dur(video_path)
    if dur <= 0:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, frac in enumerate(fracs, start=1):
        frame = out_dir / f"thumb_candidate_{i}.png"
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.1, dur * frac):.2f}",
             "-i", str(video_path), "-frames:v", "1", str(frame)],
            capture_output=True, text=True,
        )
        if r.returncode == 0 and frame.exists():
            frames.append(frame)
    return frames


def _probe_dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def generate_upload_package(cfg: dict, video_path: Path, out_dir: Path) -> Path:
    """upload_package.md + 썸네일 후보 생성 → md 경로 반환."""
    thumbs = extract_thumbnail_candidates(video_path, out_dir / "thumb_candidates")
    md = build_upload_package_md(
        cfg, video_path, suggested=suggest_upload_time(datetime.now()),
        thumbnails=thumbs,
    )
    pkg = out_dir / "upload_package.md"
    pkg.write_text(md, encoding="utf-8")
    return pkg
