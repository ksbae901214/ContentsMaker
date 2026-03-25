import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { writeFile, mkdir } from "fs/promises";
import { join } from "path";

const ROOT = process.cwd();
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // 10MB

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

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get("content-type") || "";

    if (contentType.includes("multipart/form-data")) {
      const fd = await req.formData();
      const sceneId = Number(fd.get("sceneId"));
      const file = fd.get("file") as File;
      if (!file || !Number.isInteger(sceneId) || sceneId < 1) {
        return NextResponse.json({ error: "sceneId and file required" }, { status: 400 });
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        return NextResponse.json({ error: "파일 크기 10MB 초과" }, { status: 400 });
      }

      const dir = join(ROOT, "data", "images");
      await mkdir(dir, { recursive: true });
      const timestamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
      const filename = `${timestamp}_scene_${String(sceneId).padStart(2, "0")}_upload.png`;
      const buf = Buffer.from(await file.arrayBuffer());
      const imagePath = join(dir, filename);
      await writeFile(imagePath, buf);

      return NextResponse.json({ scene_id: sceneId, image_path: imagePath, prompt: "(uploaded)" });
    }

    const body = await req.json();
    const sceneId = Number(body.sceneId);
    const prompt = String(body.prompt || "");

    if (!Number.isInteger(sceneId) || sceneId < 1 || !prompt.trim()) {
      return NextResponse.json({ error: "sceneId (int) and prompt required" }, { status: 400 });
    }

    const stdinData = JSON.stringify({ scene_id: sceneId, prompt });
    const result = JSON.parse(await pyWithStdin(`
import sys,json
sys.path.insert(0,${JSON.stringify(ROOT)})
from src.illustrator.image_generator import regenerate_single_image
args=json.loads(sys.stdin.read())
r=regenerate_single_image(args["scene_id"],args["prompt"])
print(json.dumps(r))`, stdinData));

    return NextResponse.json(result);
  } catch (e: any) {
    return NextResponse.json({ error: "이미지 생성 실패" }, { status: 500 });
  }
}
