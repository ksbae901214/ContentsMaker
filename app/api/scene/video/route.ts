import { NextRequest, NextResponse } from "next/server";
import { writeFile } from "fs/promises";
import { resolve } from "path";

const ROOT = process.cwd();
const VIDEOS_DIR = resolve(ROOT, "data", "videos");

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const sceneIdRaw = formData.get("sceneId");
    const file = formData.get("file") as File | null;

    const sceneId = Number(sceneIdRaw);
    if (!Number.isInteger(sceneId) || sceneId < 1) {
      return NextResponse.json({ error: "sceneId 필요" }, { status: 400 });
    }
    if (!file || file.size === 0) {
      return NextResponse.json({ error: "파일 필요" }, { status: 400 });
    }
    if (file.size > 200 * 1024 * 1024) {
      return NextResponse.json({ error: "파일 크기 200MB 초과" }, { status: 400 });
    }

    const filename = `scene_${String(sceneId).padStart(2, "0")}.mp4`;
    const dest = resolve(VIDEOS_DIR, filename);
    // Sanity check: must stay within VIDEOS_DIR
    if (!dest.startsWith(VIDEOS_DIR)) {
      return NextResponse.json({ error: "경로 오류" }, { status: 403 });
    }

    const buffer = Buffer.from(await file.arrayBuffer());
    await writeFile(dest, buffer);

    return NextResponse.json({ scene_id: sceneId, video_path: dest });
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "업로드 실패" }, { status: 500 });
  }
}
