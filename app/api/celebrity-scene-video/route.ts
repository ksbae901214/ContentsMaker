import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile, mkdir } from "fs/promises";
import { existsSync } from "fs";
import { join, resolve, extname } from "path";

const ROOT = process.cwd();
const ALLOWED_DIRS = [
  resolve(ROOT, "data/videos"),
  resolve(ROOT, "data/celebrity_portraits"),
];

function isSafePath(p: string): boolean {
  const full = resolve(p);
  return ALLOWED_DIRS.some((d) => full.startsWith(d)) && existsSync(full);
}

/**
 * GET /api/celebrity-scene-video?path=<abs>  → 영상 파일 스트리밍 (data/videos/ 내부만).
 * POST (multipart): file, sceneId, celebrityName (optional)
 *   → data/videos/celebrity_user/{name}_scene_{id}_{ts}.mp4 저장, 경로 반환.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const path = searchParams.get("path");
  if (!path) return new NextResponse("path required", { status: 400 });
  if (!isSafePath(path)) return new NextResponse("forbidden", { status: 403 });
  try {
    const buf = await readFile(path);
    const ext = extname(path).slice(1).toLowerCase();
    const mime = ext === "webm" ? "video/webm" : "video/mp4";
    return new NextResponse(buf, {
      headers: { "Content-Type": mime, "Cache-Control": "no-store" },
    });
  } catch (e: any) {
    return new NextResponse(`read failed: ${e.message}`, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file");
    const sceneIdRaw = (form.get("sceneId") as string) || "";
    const name = ((form.get("celebrityName") as string) || "custom").trim();
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "file required" }, { status: 400 });
    }
    const sceneId = parseInt(sceneIdRaw, 10);
    if (!Number.isFinite(sceneId) || sceneId <= 0) {
      return NextResponse.json({ error: "invalid sceneId" }, { status: 400 });
    }
    const ext = extname(file.name) || ".mp4";
    const safeName = name.replace(/[^\w가-힣-]/g, "_").slice(0, 30) || "custom";
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const destDir = resolve(ROOT, "data/videos/celebrity_user");
    const dest = join(destDir, `${safeName}_scene_${sceneId.toString().padStart(2, "0")}_${ts}${ext}`);
    if (!existsSync(destDir)) await mkdir(destDir, { recursive: true });
    const buf = Buffer.from(await file.arrayBuffer());
    await writeFile(dest, buf);
    return NextResponse.json({ path: dest, sceneId, size: buf.length });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
