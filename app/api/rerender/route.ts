import { NextRequest } from "next/server";
import { spawn } from "child_process";
import { resolve } from "path";

const ROOT = process.cwd();
const ALLOWED_SCRIPTS_DIR = resolve(ROOT, "data", "scripts");
const ALLOWED_IMAGES_DIR = resolve(ROOT, "data", "images");

function isAllowedScriptPath(p: string): boolean {
  return resolve(p).startsWith(ALLOWED_SCRIPTS_DIR);
}

function isAllowedImagePath(p: string): boolean {
  return resolve(p).startsWith(ALLOWED_IMAGES_DIR);
}

function pyWithStdin(code: string, stdinData: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", ["-c", code], { cwd: ROOT, env: { ...process.env } });
    let out = "", err = "";
    p.stdout.on("data", d => { out += d; });
    p.stderr.on("data", d => { err += d; });
    p.on("close", c => {
      if (c !== 0) reject(new Error(err.slice(-500) || `exit ${c}`));
      else { const l = out.trim().split("\n"); resolve(l[l.length - 1]); }
    });
    p.on("error", e => reject(new Error(`Python: ${e.message}`)));
    p.stdin.write(stdinData);
    p.stdin.end();
  });
}

export const maxDuration = 300;

export async function POST(req: NextRequest) {
  const { scriptPath, sceneImages, useBgm } = await req.json() as {
    scriptPath: string;
    sceneImages: { scene_id: number; image_path: string }[];
    useBgm: boolean;
  };

  if (!isAllowedScriptPath(scriptPath)) {
    return new Response(
      `data: ${JSON.stringify({ type: "error", message: "허용되지 않는 스크립트 경로" })}\n\n`,
      { headers: { "Content-Type": "text/event-stream" } },
    );
  }

  const validImages = sceneImages.filter((img) => isAllowedImagePath(img.image_path));
  const safeBgm = Boolean(useBgm);

  const enc = new TextEncoder();

  const stream = new ReadableStream({
    async start(ctrl) {
      const send = (type: string, data: any) =>
        ctrl.enqueue(enc.encode(`data: ${JSON.stringify({ type, ...data })}\n\n`));

      try {
        send("progress", { message: "🎙️ 음성 재생성 중..." });

        const ttsArgs = JSON.stringify({ script_path: scriptPath });
        const ttsResult = JSON.parse(await pyWithStdin(`
import sys,json
sys.path.insert(0,${JSON.stringify(ROOT)})
from src.analyzer.script_models import ShortsScript
from src.tts.edge_tts_generator import generate_voice_with_timing
args=json.loads(sys.stdin.read())
ap,timings=generate_voice_with_timing(ShortsScript.load(args["script_path"]))
print(json.dumps({"audio_path":str(ap),"timings":timings}))`, ttsArgs));
        send("progress", { message: `✅ 음성 완료 (${ttsResult.timings.length}씬 타이밍)` });

        send("progress", { message: "🎬 영상 재렌더링 중..." });

        const renderArgs = JSON.stringify({
          script_path: scriptPath,
          scene_images: validImages,
          use_bgm: safeBgm,
          audio_path: ttsResult.audio_path,
          timings: ttsResult.timings,
        });
        const rr = JSON.parse(await pyWithStdin(`
import sys,json
sys.path.insert(0,${JSON.stringify(ROOT)})
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video
args=json.loads(sys.stdin.read())
s=ShortsScript.load(args["script_path"])
ap=Path(args["audio_path"])
si=args["scene_images"] if args["scene_images"] else None
timings=args.get("timings")
o=render_video(s,audio_path=ap,scene_images=si,use_bgm=args["use_bgm"],scene_timings=timings)
print(json.dumps({"path":str(o),"size":round(o.stat().st_size/(1024*1024),1)}))`, renderArgs));
        send("progress", { message: `✅ 렌더링 완료 (${rr.size}MB)` });

        send("done", { result: { videoPath: rr.path, size: rr.size } });
      } catch (e: any) {
        send("error", { message: "재렌더링 실패" });
      }
      ctrl.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      "CF-Cache-Status": "DYNAMIC",
    },
  });
}
