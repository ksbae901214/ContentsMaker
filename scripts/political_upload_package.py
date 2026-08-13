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

from scripts.shorts_category import (
    DEFAULT_CATEGORY, record_category, resolve_config_category,
)

TITLE_MIN, TITLE_MAX = 15, 30          # 030 벤치마크: 훅 제목 15~30자
# 036: 카테고리 원장 — 업로드가 수동이라 유튜브 쪽엔 카테고리가 남지 않는다.
# 여기서 기록해 두어야 다음 성과 리포트가 카테고리별로 쪼개진다.
CATEGORY_LEDGER_PATH = Path("data/channel_analytics/category_ledger.json")
MAX_HASHTAGS = 4                        # #인물명 2~4개 권장
UPLOAD_HOUR = 20                        # 평일 20~21시 직후 업로드 권장
# 035: 열린 질문은 실측 댓글율 0.24% — 편이 갈리는 선택지형으로 교체
DEFAULT_PINNED_COMMENT = "둘 중 누가 더 문제라고 보세요? ① 여당  ② 야당 — 번호로 답글 👇"

# 035 소재 프레임: '누가 누구를 저격'(공방형)은 실측상 1,100대 천장.
# 터진 영상은 전부 결과가 난 사건 — '13시간 대역전극', '9년 침묵의 컴백'.
_CLASH_WORDS = (
    "직격", "저격", "공방", "정면충돌", "충돌", "맞불", "발끈", "일침", "일갈",
    "돌직구", "질타", "성토", "반박", "역공", "설전",
)
_OUTCOME_WORDS = (
    "결국", "끝내", "만에", "끝에", "무산", "철회", "사퇴", "취소", "번복",
    "뒤집", "역전", "확정", "통과", "부결", "폐기", "좌초", "컴백", "복귀",
    "실형", "선고", "기각", "인용", "합의", "타결", "구속", "해임", "경질",
)

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


def _domain(category: str):
    """036: 카테고리별 규칙 팩 조회 (순환 import 회피용 지연 import)."""
    from scripts.shorts_domain import rules_for
    return rules_for(category)


def domain_warnings(cfg: dict) -> list[str]:
    """036 Phase 2 도메인 주의 경고 (사회 피의사실·연예 미확인 사생활 등)."""
    from scripts.shorts_domain import domain_warnings as _warn
    return _warn(cfg)


def is_clash_frame(title: str, category: str = DEFAULT_CATEGORY) -> bool:
    """'A가 B를 직격/저격' 공방형 프레임인지."""
    clean, _ = sanitize_yt_title(title)
    return any(w in clean for w in _domain(category).clash_words)


def has_outcome_frame(title: str, category: str = DEFAULT_CATEGORY) -> bool:
    """결과·전환이 드러나는 사건 프레임인지 (대역전극·컴백·철회·동결·무죄…)."""
    clean, _ = sanitize_yt_title(title)
    return any(w in clean for w in _domain(category).outcome_words)


def lint_topic_frame(title: str, category: str = DEFAULT_CATEGORY) -> list[str]:
    """035 소재 프레임 경고 — 결과 없는 공방형은 실측상 1,100대 천장.

    036: 결과어·예시는 카테고리별 (경제 '동결', 사회 '무죄', 연예 '하차'…).
    """
    if is_clash_frame(title, category) and not has_outcome_frame(title, category):
        return ["결과 없는 공방형 소재 — '결과가 난 사건'으로 프레임을 바꾸세요 "
                f"(예: {_domain(category).outcome_example}). "
                "실측상 공방형은 조회수 1,100대에서 멈춥니다 (035)"]
    return []


def resolve_pinned_comment(cfg: dict) -> str:
    """고정댓글 — 명시값 > cta.voice(중반 CTA와 동일 질문) > 카테고리 기본 선택지형."""
    from scripts.shorts_domain import rules_for_config
    return (cfg.get("pinned_comment")
            or (cfg.get("cta") or {}).get("voice")
            or rules_for_config(cfg).default_pinned_comment)


def lint_yt_title(title: str, persons: list[str] | None = None,
                  category: str = DEFAULT_CATEGORY) -> list[str]:
    """030 제목 공식(15~30자, 앵커 포함) + 035 소재 프레임 점검 경고.

    036: 제목 앵커는 카테고리별 — 정치는 실명, 경제는 숫자·기관명.
    """
    warnings = []
    n = len(title)
    if n < TITLE_MIN:
        warnings.append(f"제목 {n}자 — {TITLE_MIN}자 이상 권장 (구체성 부족)")
    elif n > TITLE_MAX:
        warnings.append(f"제목 {n}자 — {TITLE_MAX}자 이하 권장 (모바일 잘림)")
    if persons and not any(p in title for p in persons):
        warnings.append(
            f"제목에 {_domain(category).anchor_label} 미포함 — 1~2개 권장")
    if any(w in title for w in ("속보", "충격!")):
        warnings.append("'속보/충격!'형 제목은 실측상 천장이 낮음 — 서사형 권장")
    if TITLE_HASHTAG_RE.search(title):
        warnings.append("제목에 해시태그 포함 — 설명란으로 이동 "
                        "(쇼츠 피드 제목 잘림·스팸 인상, 034)")
    if is_report_style(title):
        warnings.append("보도체 제목 — 감정훅/호기심형 권장 (034 벤치마크)")
    warnings.extend(lint_topic_frame(title, category))
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
    category = resolve_config_category(cfg)
    warnings = lint_yt_title(yt_title_raw, cfg.get("persons"), category)
    warnings.extend(domain_warnings(cfg))
    lines = [
        f"# 업로드 패키지 — {cfg['slug']}",
        "",
        f"**영상**: `{video_path}`",
        f"**카테고리**: `{category}` — 성과 원장에 기록됨 (036, 카테고리별 리포트용)",
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
        resolve_pinned_comment(cfg),
        "```",
    ]
    if thumbnails:
        lines += ["", "## 썸네일 후보"]
        lines.extend(f"- `{t}`" for t in thumbnails)
    rules = _domain(category)
    lines += ["", f"## 업로드 전 체크리스트 ({rules.label}, 034/035/036)"]
    lines.extend(f"- [ ] {item}" for item in rules.checklist)
    lines += [
        "",
        "---",
        f"⚠️ {rules.label} 콘텐츠 — 검수 후 **수동 업로드** "
        "(FR-020/021 자동 업로드 차단 유지).",
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


def generate_upload_package(cfg: dict, video_path: Path, out_dir: Path,
                            ledger_path: Path | None = None) -> Path:
    """upload_package.md + 썸네일 후보 생성 → md 경로 반환.

    036: 제목·카테고리를 카테고리 원장에 함께 기록한다 (성과 리포트의 카테고리
    슬라이스 근거). 원장 기록은 계측 보조라 실패해도 패키지 생성을 막지 않는다.
    """
    thumbs = extract_thumbnail_candidates(video_path, out_dir / "thumb_candidates")
    md = build_upload_package_md(
        cfg, video_path, suggested=suggest_upload_time(datetime.now()),
        thumbnails=thumbs,
    )
    pkg = out_dir / "upload_package.md"
    pkg.write_text(md, encoding="utf-8")

    try:
        record_category(
            ledger_path or CATEGORY_LEDGER_PATH,
            cfg.get("yt_title") or cfg["title"],
            resolve_config_category(cfg),
            slug=cfg.get("slug", ""),
        )
    except OSError as e:
        print(f"   ⚠️ 카테고리 원장 기록 실패 (계측만 영향): {e}")
    return pkg
