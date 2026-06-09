import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

const ROOT = process.cwd();
const PHOTOS_DIR = path.join(ROOT, "data", "politician_cards", "photos");

/**
 * GET /api/jpolitics/photo/[name]
 *
 * 정치인 사진 스트림 (검수 화면 미리보기용).
 * 미존재 시 404 — 클라이언트가 회색 실루엣 폴백 처리 (FR-027).
 */
export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  const { name } = await params;
  const safeName = decodeURIComponent(name).replace(/[\\/]/g, "");
  // 확장자 후보 순회
  const candidates = [".jpg", ".jpeg", ".png", ".webp"];
  let filePath: string | null = null;
  for (const ext of candidates) {
    const candidate = path.join(PHOTOS_DIR, `${safeName}${ext}`);
    if (existsSync(candidate)) {
      filePath = candidate;
      break;
    }
  }
  // 캐시 디렉토리에 prefix_xx.jpg 형식으로 저장된 경우도 검색
  if (!filePath) {
    const altPath = path.join(PHOTOS_DIR, `${safeName}_0.jpg`);
    if (existsSync(altPath)) filePath = altPath;
  }
  if (!filePath) {
    return NextResponse.json(
      { ok: false, error: "photo_not_found" },
      { status: 404 }
    );
  }
  const buf = await readFile(filePath);
  const ext = path.extname(filePath).toLowerCase();
  const contentType =
    ext === ".png" ? "image/png" : ext === ".webp" ? "image/webp" : "image/jpeg";
  return new NextResponse(buf, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=3600",
    },
  });
}
