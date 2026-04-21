import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

/**
 * GET /api/celebrity-scene-prompt?scriptPath=...&sceneId=N&celebrityName=...
 *   → 해당 씬의 Freepik image-to-video 모션 프롬프트 + image_query 반환.
 *   사용자가 "직접 생성할 수 있게 프롬프트도 제공" 요청.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const scriptPath = searchParams.get("scriptPath");
  const sceneIdStr = searchParams.get("sceneId");
  const celebrityName = searchParams.get("celebrityName") || "";
  if (!scriptPath || !sceneIdStr) {
    return NextResponse.json({ error: "scriptPath and sceneId required" }, { status: 400 });
  }
  const sceneId = parseInt(sceneIdStr, 10);

  const code = `
import sys, json
sys.path.insert(0, "${ROOT}")
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video_gen.celebrity_motion import build_celebrity_motion_prompt

s = ShortsScript.load(Path("""${scriptPath}"""))
target = next((x for x in s.scenes if x.id == ${sceneId}), None)
if target is None:
    print(json.dumps({"error": "scene not found"}))
    sys.exit(0)
motion = build_celebrity_motion_prompt(target, ${JSON.stringify(celebrityName)})
print(json.dumps({
  "motion_prompt": motion,
  "image_query": target.image_query or "",
  "voice_text": target.voice_text,
  "scene_id": target.id,
  "type": target.type,
  "emphasis": target.emphasis,
}, ensure_ascii=False))
`;
  return await runPy(code);
}

async function runPy(code: string): Promise<NextResponse> {
  return new Promise((resolve) => {
    const p = spawn("python3", ["-c", code], { cwd: ROOT, env: { ...process.env } });
    let out = "", err = "";
    p.stdout.on("data", (d) => { out += d; });
    p.stderr.on("data", (d) => { err += d; });
    p.on("close", (c) => {
      if (c !== 0) {
        resolve(NextResponse.json({ error: err.slice(-300) || `exit ${c}` }, { status: 500 }));
        return;
      }
      try {
        const lines = out.trim().split("\n");
        const last = lines[lines.length - 1];
        resolve(NextResponse.json(JSON.parse(last)));
      } catch (e: any) {
        resolve(NextResponse.json({ error: `parse failed: ${e.message}` }, { status: 500 }));
      }
    });
  });
}
