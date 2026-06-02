import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile, mkdir } from "fs/promises";
import { existsSync } from "fs";
import { join, resolve, extname, basename } from "path";

const ROOT = process.cwd();
const ALLOWED_DIR = resolve(ROOT, "data/celebrity_portraits");

function isSafePath(p: string): boolean {
  const full = resolve(p);
  return full.startsWith(ALLOWED_DIR) && existsSync(full);
}

/**
 * GET /api/celebrity-portrait?path=<absolute-path>
 *   → data/celebrity_portraits/ 내부 파일만 스트리밍.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const path = searchParams.get("path");
  if (!path) return new NextResponse("path required", { status: 400 });
  if (!isSafePath(path)) return new NextResponse("forbidden", { status: 403 });

  try {
    const buf = await readFile(path);
    const ext = extname(path).slice(1).toLowerCase();
    const mime = ext === "png" ? "image/png" : ext === "webp" ? "image/webp" : "image/jpeg";
    return new NextResponse(buf, {
      headers: {
        "Content-Type": mime,
        "Cache-Control": "no-store",
      },
    });
  } catch (e: any) {
    return new NextResponse(`read failed: ${e.message}`, { status: 500 });
  }
}

/**
 * POST /api/celebrity-portrait  (multipart/form-data)
 *   file: 이미지 파일
 *   name: (optional) 인물명 prefix
 *   → 저장된 절대 경로를 JSON으로 반환.
 */
export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file");
    const name = ((form.get("name") as string) || "custom").trim();
    if (!(file instanceof File)) {
      return NextResponse.json({ error: "file required" }, { status: 400 });
    }
    const ext = extname(file.name) || ".jpg";
    const safeName = name.replace(/[^\w가-힣-]/g, "_").slice(0, 30) || "custom";
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const filename = `${safeName}_${ts}_user${ext}`;
    const dest = join(ALLOWED_DIR, filename);
    if (!existsSync(ALLOWED_DIR)) await mkdir(ALLOWED_DIR, { recursive: true });
    const buf = Buffer.from(await file.arrayBuffer());
    await writeFile(dest, buf);
    return NextResponse.json({
      path: dest,
      filename,
      size: buf.length,
    });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
