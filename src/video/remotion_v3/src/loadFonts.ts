/**
 * V3 폰트 로더 — Noto Sans KR (Google Fonts) Black + Bold.
 * PinnedHeadline 노란 박스 + SubtitleBlock 자막용.
 *
 * V1/V2 Remotion 폰트와 분리 (격리 모드).
 */
import { continueRender, delayRender } from "remotion";

let loaded = false;

export async function loadFonts(): Promise<void> {
  if (loaded) return;
  const handle = delayRender("Loading Noto Sans KR fonts for V3");
  try {
    const fontFace900 = new FontFace(
      "Noto Sans KR",
      "url(https://fonts.gstatic.com/s/notosanskr/v36/PbykFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzuoyeLTq8H4hfeE.woff2)",
      { weight: "900", style: "normal" },
    );
    const fontFace700 = new FontFace(
      "Noto Sans KR",
      "url(https://fonts.gstatic.com/s/notosanskr/v36/PbykFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzuoyeLTq8H4hfeE.woff2)",
      { weight: "700", style: "normal" },
    );
    await Promise.all([fontFace900.load(), fontFace700.load()]);
    (document.fonts as unknown as { add: (f: FontFace) => void }).add(
      fontFace900,
    );
    (document.fonts as unknown as { add: (f: FontFace) => void }).add(
      fontFace700,
    );
    loaded = true;
  } finally {
    continueRender(handle);
  }
}
