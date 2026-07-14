import { NextRequest } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

// cut (~30s) + Remotion render (~180s) = 3.5 min, buffer to 15 min
export const maxDuration = 900;

function runPy(pyCode: string): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", ["-c", pyCode], { cwd: ROOT, env: { ...process.env } });
    let stdout = "";
    let stderr = "";
    p.stdout.on("data", (d) => { stdout += d; });
    p.stderr.on("data", (d) => { stderr += d; });
    p.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(stderr.slice(-1000) || `exit ${code}`));
      } else {
        resolve({ stdout, stderr });
      }
    });
    p.on("error", (e) => reject(new Error(`Python: ${e.message}`)));
  });
}

function lastLine(stdout: string): string {
  const lines = stdout.trim().split("\n");
  return lines[lines.length - 1];
}

/**
 * POST /api/jpolitics/render
 *
 * Body: { workDir: string, momentIdx: number, cropX?: number, pad?: number }
 * Response: SSE stream with progress and done/error events
 */
export async function POST(req: NextRequest) {
  let body: { workDir?: string; momentIdx?: number; cropX?: number; pad?: number };
  try {
    body = await req.json();
  } catch {
    return new Response("JSON body required", { status: 400 });
  }

  const workDir = (body.workDir || "").trim();
  const momentIdx = typeof body.momentIdx === "number" ? body.momentIdx : 1;
  const cropX = typeof body.cropX === "number" ? body.cropX : 0.5;
  const pad = typeof body.pad === "number" ? body.pad : 0.5;

  if (!workDir) {
    return new Response("workDir required", { status: 400 });
  }

  const enc = new TextEncoder();

  const stream = new ReadableStream({
    async start(ctrl) {
      const send = (type: string, data: Record<string, unknown>) => {
        try {
          ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type, ...data })}\n\n`));
        } catch {
          // controller closed
        }
      };

      const cutCode = `
import sys, json
sys.path.insert(0, '${ROOT}')
from pathlib import Path
from src.jpolitics.models.moment import MomentDetectionResult
from src.jpolitics.video.clip_maker import ClipMakeError, make_moment_clip
from src.jpolitics.video.captions import build_caption_cues, save_caption_cues

work_dir = Path(${JSON.stringify(workDir)})
moments_path = work_dir / "moments.json"
detection = MomentDetectionResult.from_dict(json.loads(moments_path.read_text()))
top_moments = list(detection.top(len(detection.moments)))
n = ${momentIdx}
moment = top_moments[n - 1]

mp4_candidates = sorted(
    (p for p in work_dir.glob("*.mp4") if not p.name.startswith("scene_") and not p.name.startswith("clip_") and not p.name.startswith("output_")),
    key=lambda p: p.stat().st_mtime,
)
source_video = mp4_candidates[-1]
output_path = work_dir / f"clip_{n}.mp4"

clip_result = make_moment_clip(
    source_video=source_video,
    moment=moment,
    output_path=output_path,
    pad_before=${pad},
    pad_after=${pad},
    crop_x=${cropX},
)
json_path = clip_result.save(work_dir, n)

try:
    cues = build_caption_cues(
        work_dir=work_dir,
        source_url=detection.source_url,
        video_path=source_video,
        moment=moment,
        pad_before=${pad},
    )
except Exception:
    cues = []
captions_path = save_caption_cues(cues, work_dir, n)

print(json.dumps({
    "clipPath": str(output_path),
    "captionsCount": len(cues),
    "durationSec": clip_result.duration_sec,
}, ensure_ascii=False))
`;

      const renderCode = `
import sys, json
sys.path.insert(0, '${ROOT}')
from pathlib import Path
from datetime import datetime
from src.jpolitics.models.clip import CaptionCue, ClipResult
from src.jpolitics.models.moment import MomentDetectionResult
from src.jpolitics.video.renderer import RenderError, render_moment_short

work_dir = Path(${JSON.stringify(workDir)})
n = ${momentIdx}

clip_json = work_dir / f"clip_{n}.json"
clip_result = ClipResult.from_dict(json.loads(clip_json.read_text()))

captions_json = work_dir / f"captions_{n}.json"
captions = []
if captions_json.exists():
    raw = json.loads(captions_json.read_text())
    captions = [CaptionCue.from_dict(c) for c in raw]

channel = ""
source_date = datetime.now().strftime("%Y.%m.%d")
moments_json = work_dir / "moments.json"
if moments_json.exists():
    meta = json.loads(moments_json.read_text())
    channel = meta.get("channel", "")
    parts = work_dir.name.split("_")
    if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
        raw_d = parts[0]
        source_date = f"{raw_d[:4]}.{raw_d[4:6]}.{raw_d[6:8]}"

output_path = work_dir / f"output_{n}.mp4"
try:
    result_path = render_moment_short(
        clip_result=clip_result,
        captions=captions,
        channel=channel,
        source_date=source_date,
        output_path=output_path,
    )
    print(json.dumps({"outputPath": str(result_path)}, ensure_ascii=False))
except RenderError as e:
    print(json.dumps({"error": "render_failed", "detail": str(e)[:400]}))
`;

      try {
        send("progress", { message: "✂️ 클립 컷 중..." });
        const cutResult = await runPy(cutCode);
        const cutParsed = JSON.parse(lastLine(cutResult.stdout));
        send("progress", {
          message: `✂️ 클립 완료 (${cutParsed.durationSec?.toFixed(1) ?? "?"}초, 자막 ${cutParsed.captionsCount ?? 0}개)`,
        });

        send("progress", { message: "🎬 Remotion 렌더 중 (1~3분)..." });
        const renderResult = await runPy(renderCode);
        const renderParsed = JSON.parse(lastLine(renderResult.stdout));

        if (renderParsed.error) {
          send("error", { message: renderParsed.detail || renderParsed.error });
        } else {
          send("done", { outputPath: renderParsed.outputPath });
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        send("error", { message: msg.slice(0, 500) });
      } finally {
        ctrl.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
