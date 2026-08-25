"""기사 캡처 → 정치쇼츠 문서 씬 소스(`src_<key>.mp4`) 생성.

당사자 육성 영상이 없는 소재(전언 보도·보도자료 등)에서, 기사 화면을 띄우고
TTS가 발언 원문을 읽어주는 씬을 만들기 위한 도구다. 정지 이미지를 그대로 쓰면
프레임이 죽어 보이므로 세로 팬(헤드라인 → 본문)을 걸어 mp4로 굽는다.

렌더 스크립트는 `src_<key>.mp4` 가 이미 있으면 다운로드를 건너뛰므로, 이 파일을
work_dir 에 미리 배치한 뒤 config `sources` 에 키만 등록하면 된다.

Usage:
    PYTHONPATH=. .venv311/bin/python scripts/capture_article.py \
        <article_url> <slug> [--key doc] [--seconds 15]

주의: 네이버 뉴스는 Claude in Chrome 확장으로는 차단되지만 Playwright(로컬
크로미움)로는 접근된다. 광고 제거 셀렉터에 `[class*="ad_"]` 를 쓰면
`media_end_head_headline`(…he**ad_**headline)까지 지워지니 정확히 지정할 것.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CLIP_TOP, CLIP_LEFT, CLIP_WIDTH = 98.0, 100.0, 700.0   # 네이버 뉴스 본문 기준
# 출력은 **16:9** — 다른 소스(방송 영상)와 같은 비율이라야 Remotion 이 레터박스를
# 남기고, `subtitle_position: "bottom"` 자막이 기사 본문 위가 아니라 그 아래에
# 깔린다 (2026-08-12 실측: 9:16 로 만들었더니 자막이 본문을 덮었다).
OUT_W, OUT_H = 1080, 608
# 창 높이의 2배로 캡처해 헤드라인 → 부제 → 사진 순으로 세로 팬한다.
# 가로는 절대 크롭하지 않는다 — 헤드라인 양끝 글자가 잘린다.
PAN_FACTOR = 2.0

# 광고·플로팅만 정확히 지정 (헤드라인·본문은 절대 건드리지 않는다)
_STRIP_SELECTOR = (
    "iframe, ._DYNAMIC_AD, .media_end_linked, "
    ".media_end_head_autosummary, .ad_wrap, .promotion"
)


def capture_png(url: str, out: Path) -> None:
    """기사 헤드라인~리드 영역을 캡처 (16:9 창 높이의 PAN_FACTOR 배)."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": 900, "height": 1400},
                device_scale_factor=2,
                user_agent=UA,
            )
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_selector("#dic_area", timeout=20_000)
            page.evaluate(
                f"document.querySelectorAll('{_STRIP_SELECTOR}')"
                ".forEach(el => el.remove());"
            )
            page.wait_for_timeout(800)   # 본문 이미지 로드 안정화
            page.screenshot(path=str(out), clip={
                "x": CLIP_LEFT, "y": CLIP_TOP,
                "width": CLIP_WIDTH,
                "height": CLIP_WIDTH * OUT_H / OUT_W * PAN_FACTOR,
            })
        except Exception as exc:
            raise RuntimeError(f"기사 캡처 실패 ({url}): {exc}") from exc
        finally:
            browser.close()


def build_pan_mp4(png: Path, out: Path, seconds: int) -> None:
    """정지 PNG → 세로 팬 mp4 (헤드라인에서 본문 쪽으로 천천히 내려감)."""
    pan_range = int(OUT_H * PAN_FACTOR) - OUT_H
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-t", str(seconds), "-i", str(png),
         "-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"scale={OUT_W}:-2,"
                f"crop={OUT_W}:{OUT_H}:0:"
                f"'min({pan_range},{pan_range}*t/{seconds - 1})',"
                "fps=30,format=yuv420p",
         "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-shortest", str(out)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"팬 영상 생성 실패: {result.stderr.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="기사 URL (네이버 뉴스 본문 페이지)")
    ap.add_argument("slug", help="config 의 slug — data/political_pro/<slug>/")
    ap.add_argument("--key", default="doc", help="sources 키 (기본 doc)")
    ap.add_argument("--seconds", type=int, default=15, help="소스 길이 (기본 15s)")
    args = ap.parse_args()

    wd = Path("data/political_pro") / args.slug
    wd.mkdir(parents=True, exist_ok=True)
    png = wd / f"{args.key}_card.png"
    mp4 = wd / f"src_{args.key}.mp4"

    capture_png(args.url, png)
    print(f"✅ 캡처: {png} ({png.stat().st_size // 1024} KB)")
    build_pan_mp4(png, mp4, args.seconds)
    print(f"✅ 소스: {mp4} ({args.seconds}s)")
    print(f"\n🔎 {png} 를 열어 헤드라인·인용문이 잘렸는지 확인하세요.")
    print(f"   config sources 에 \"{args.key}\": {{ \"verify_frac\": 0.2 }} 등록 후 "
          "download 를 돌리면 이 파일을 그대로 씁니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
