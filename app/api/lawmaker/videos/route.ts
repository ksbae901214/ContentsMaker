import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { resolve } from "path";

const ROOT = process.cwd();

function runPython(script: string): Promise<string> {
  return new Promise((res, rej) => {
    const proc = spawn("python3", ["-c", script], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT },
    });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { err += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) res(out.trim());
      else rej(new Error(err || `exit ${code}`));
    });
  });
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get("name");
  const source = searchParams.get("source") || "all";
  const limit = Math.min(parseInt(searchParams.get("limit") || "10", 10), 20);

  if (!name || name.trim().length === 0) {
    return NextResponse.json({ error: "name 파라미터가 필요합니다" }, { status: 400 });
  }

  const safeName = name.replace(/['"\\]/g, "");
  const safeSource = ["all", "natv", "news"].includes(source) ? source : "all";

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.scraper.lawmaker_video_finder import search_lawmaker_videos, VideoSearchError, format_duration, format_upload_date

try:
    videos = search_lawmaker_videos(${JSON.stringify(safeName)}, ${JSON.stringify(safeSource)}, ${limit})
    for v in videos:
        v['duration_label'] = format_duration(v['duration_seconds'])
        v['date_label'] = format_upload_date(v['upload_date'])
    print(json.dumps(videos, ensure_ascii=False))
except VideoSearchError as e:
    print(json.dumps({"error": str(e)}))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);

    if ("error" in data) {
      return NextResponse.json({ error: data.error, videos: [] }, { status: 200 });
    }

    return NextResponse.json({ videos: data });
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "영상 검색 실패", videos: [] },
      { status: 200 }
    );
  }
}
