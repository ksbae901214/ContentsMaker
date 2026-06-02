import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { resolve } from "path";
import { spawn } from "child_process";

const ROOT = process.cwd();
const ALLOWED_DIR = resolve(ROOT, "data", "scripts");

function isAllowedPath(p: string): boolean {
  const resolved = resolve(p);
  return resolved.startsWith(ALLOWED_DIR);
}

function runPython(script: string): Promise<string> {
  return new Promise((res, rej) => {
    const proc = spawn("python3", ["-c", script], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT },
    });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { err += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) res(out.trim());
      else rej(new Error(err || `exit ${code}`));
    });
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as { scriptPath: string; imageStyle?: string };
    const { scriptPath, imageStyle = "realistic" } = body;

    if (!scriptPath) {
      return NextResponse.json({ error: "scriptPath required" }, { status: 400 });
    }
    if (!isAllowedPath(scriptPath)) {
      return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
    }

    await readFile(scriptPath, "utf-8"); // verify file exists

    const pyScript = `
import json, sys
sys.path.insert(0, '${ROOT}')
from src.analyzer.script_models import ShortsScript
from src.illustrator.prompt_builder import build_image_prompts_simple
from src.video_gen.motion_prompt_builder import build_motion_prompt

with open(${JSON.stringify(scriptPath)}) as f:
    data = json.load(f)

s = ShortsScript.from_dict(data)
img_prompts = build_image_prompts_simple(s, ${JSON.stringify(imageStyle)})
img_map = {p['scene_id']: p['prompt'] for p in img_prompts}

result = []
for scene in s.scenes:
    result.append({
        'scene_id': scene.id,
        'type': scene.type,
        'text': scene.text,
        'voice_text': scene.voice_text,
        'image_prompt': img_map.get(scene.id, ''),
        'motion_prompt': build_motion_prompt(scene),
    })

print(json.dumps(result, ensure_ascii=False))
`;

    const output = await runPython(pyScript);
    const prompts = JSON.parse(output);

    return NextResponse.json({ prompts });
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "프롬프트 생성 실패" }, { status: 500 });
  }
}
