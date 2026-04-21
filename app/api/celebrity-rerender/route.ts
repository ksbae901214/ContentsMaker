import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { writeFile, mkdir } from "fs/promises";
import { existsSync } from "fs";
import { join, resolve as pathResolve } from "path";
import { v4 as uuid } from "uuid";

const ROOT = process.cwd();

/**
 * POST /api/celebrity-rerender
 *   body (JSON): { scriptPath, audioPath?, sceneVideoMap?, sceneImageMap? }
 *     sceneVideoMap: {scene_id: video_path}  — 유저가 교체·업로드한 씬 영상
 *     sceneImageMap: {scene_id: image_path}  — 이미지 기반 (비디오 없을 때)
 *   → render_video만 재실행해 새 MP4 생성, path 반환.
 *   기존 MP4는 덮어쓰지 않고 별도 파일로 저장.
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const scriptPath = (body.scriptPath || "").trim();
    const audioPath = (body.audioPath || "").trim();
    const sceneVideoMap = body.sceneVideoMap || {};
    const sceneImageMap = body.sceneImageMap || {};
    if (!scriptPath) {
      return NextResponse.json({ error: "scriptPath required" }, { status: 400 });
    }

    // 맵을 tmp JSON에 저장
    const tmpDir = join(ROOT, "data", "tmp");
    if (!existsSync(tmpDir)) await mkdir(tmpDir, { recursive: true });
    const mapFile = join(tmpDir, `rerender_${uuid()}.json`);
    await writeFile(mapFile, JSON.stringify({
      script_path: scriptPath,
      audio_path: audioPath,
      scene_video_map: sceneVideoMap,
      scene_image_map: sceneImageMap,
    }), "utf-8");

    // Python으로 render_video만 재호출
    const code = `
import sys, json
sys.path.insert(0, "${ROOT}")
from pathlib import Path
from src.analyzer.script_models import ShortsScript
from src.video.renderer import render_video

cfg = json.loads(Path("""${mapFile}""").read_text(encoding="utf-8"))
script = ShortsScript.load(Path(cfg["script_path"]))
audio = Path(cfg["audio_path"]) if cfg.get("audio_path") else None
video_map = {int(k): v for k, v in (cfg.get("scene_video_map") or {}).items()}
image_map = {int(k): v for k, v in (cfg.get("scene_image_map") or {}).items()}

scene_videos = [{"scene_id": sid, "video_path": p} for sid, p in video_map.items() if p]
scene_images = [{"scene_id": sid, "image_path": p} for sid, p in image_map.items() if p]

out = render_video(
    script,
    audio_path=audio if audio and audio.exists() else None,
    scene_images=scene_images or None,
    scene_videos=scene_videos or None,
    use_bgm=True,
)
print(json.dumps({"video_path": str(out)}, ensure_ascii=False))
`;

    return await new Promise<NextResponse>((resolve) => {
      const p = spawn("python3", ["-c", code], { cwd: ROOT, env: { ...process.env } });
      let out = "", err = "";
      p.stdout.on("data", (d) => { out += d; });
      p.stderr.on("data", (d) => { err += d; });
      p.on("close", (c) => {
        if (c !== 0) {
          resolve(NextResponse.json({ error: err.slice(-400) || `exit ${c}` }, { status: 500 }));
          return;
        }
        try {
          const lines = out.trim().split("\n");
          const last = lines[lines.length - 1];
          resolve(NextResponse.json(JSON.parse(last)));
        } catch (e: any) {
          resolve(NextResponse.json({ error: `parse: ${e.message}` }, { status: 500 }));
        }
      });
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
