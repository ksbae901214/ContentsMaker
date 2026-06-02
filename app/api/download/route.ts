import { NextRequest, NextResponse } from "next/server";
import { readFile, stat } from "fs/promises";
import { basename, resolve, isAbsolute } from "path";

const ALLOWED_DIRS = ["data/outputs", "data/images", "data/audio"];

export async function GET(req: NextRequest) {
  const rawPath = req.nextUrl.searchParams.get("path");
  if (!rawPath) return NextResponse.json({ error: "path 필요" }, { status: 400 });

  // Resolve to absolute path (handles both relative and absolute)
  const absPath = isAbsolute(rawPath) ? rawPath : resolve(process.cwd(), rawPath);

  // Security: no path traversal, must be under an allowed directory
  if (absPath.includes("..")) {
    return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
  }

  const cwd = process.cwd();
  const resolvedCwd = resolve(cwd);
  const isAllowed = ALLOWED_DIRS.some((dir) => {
    const allowedAbsDir = resolve(resolvedCwd, dir);
    return absPath.startsWith(allowedAbsDir + "/") || absPath === allowedAbsDir;
  });

  if (!isAllowed) {
    return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
  }

  try {
    const s = await stat(absPath);
    const buf = await readFile(absPath);
    const ext = absPath.split(".").pop()?.toLowerCase() || "";

    const contentTypes: Record<string, string> = {
      mp4: "video/mp4",
      mp3: "audio/mpeg",
      wav: "audio/wav",
      png: "image/png",
      jpg: "image/jpeg",
      jpeg: "image/jpeg",
      webp: "image/webp",
    };
    const contentType = contentTypes[ext] || "application/octet-stream";
    const isMedia = ["mp3", "wav", "png", "jpg", "jpeg", "webp"].includes(ext);
    const disposition = isMedia ? "inline" : `attachment; filename="${encodeURIComponent(basename(absPath))}"`;

    return new Response(buf, {
      headers: {
        "Content-Type": contentType,
        "Content-Length": s.size.toString(),
        "Content-Disposition": disposition,
      },
    });
  } catch {
    return NextResponse.json({ error: "파일 없음" }, { status: 404 });
  }
}
