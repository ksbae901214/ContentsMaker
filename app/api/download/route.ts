import { NextRequest, NextResponse } from "next/server";
import { readFile, stat } from "fs/promises";
import { basename } from "path";

export async function GET(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path");
  if (!path) return NextResponse.json({ error: "path 필요" }, { status: 400 });
  if (!path.includes("/data/outputs/") || path.includes(".."))
    return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
  try {
    const s = await stat(path);
    const buf = await readFile(path);
    return new Response(buf, {
      headers: {
        "Content-Type": "video/mp4",
        "Content-Length": s.size.toString(),
        "Content-Disposition": `attachment; filename="${encodeURIComponent(basename(path))}"`,
      },
    });
  } catch { return NextResponse.json({ error: "파일 없음" }, { status: 404 }); }
}
