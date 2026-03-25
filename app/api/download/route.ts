import { NextRequest, NextResponse } from "next/server";
import { readFile, stat } from "fs/promises";
import { basename } from "path";

export async function GET(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path");
  if (!path) return NextResponse.json({ error: "path 필요" }, { status: 400 });
  const isAllowed = (path.includes("/data/outputs/") || path.includes("/data/images/")) && !path.includes("..");
  if (!isAllowed)
    return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
  try {
    const s = await stat(path);
    const buf = await readFile(path);
    const isImage = path.endsWith(".png") || path.endsWith(".jpg") || path.endsWith(".jpeg") || path.endsWith(".webp");
    const contentType = isImage ? "image/png" : "video/mp4";
    const disposition = isImage ? "inline" : `attachment; filename="${encodeURIComponent(basename(path))}"`;
    return new Response(buf, {
      headers: {
        "Content-Type": contentType,
        "Content-Length": s.size.toString(),
        "Content-Disposition": disposition,
      },
    });
  } catch { return NextResponse.json({ error: "파일 없음" }, { status: 404 }); }
}
