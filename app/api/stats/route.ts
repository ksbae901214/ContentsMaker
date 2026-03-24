import { NextResponse } from "next/server";
import { readdir, stat } from "fs/promises";
import { join } from "path";

const ROOT = process.cwd();
const DATA = join(ROOT, "data");

async function countFiles(dir: string, ext: string): Promise<number> {
  try {
    const files = await readdir(dir);
    return files.filter((f) => f.endsWith(ext)).length;
  } catch {
    return 0;
  }
}

async function dirSizeMB(dir: string, ext: string): Promise<number> {
  try {
    const files = await readdir(dir);
    let total = 0;
    for (const f of files) {
      if (!f.endsWith(ext)) continue;
      const s = await stat(join(dir, f));
      total += s.size;
    }
    return Math.round((total / (1024 * 1024)) * 10) / 10;
  } catch {
    return 0;
  }
}

export async function GET() {
  const [imageCount, videoCount, audioCount, scriptCount, videoSizeMB] =
    await Promise.all([
      countFiles(join(DATA, "images"), ".png"),
      countFiles(join(DATA, "outputs"), ".mp4"),
      countFiles(join(DATA, "audio"), ".mp3"),
      countFiles(join(DATA, "scripts"), ".json"),
      dirSizeMB(join(DATA, "outputs"), ".mp4"),
    ]);

  const imageCost = imageCount * 0.005;

  return NextResponse.json({
    imageCount,
    videoCount,
    audioCount,
    scriptCount,
    imageCost,
    videoSizeMB,
  });
}
