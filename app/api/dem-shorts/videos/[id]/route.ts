// T037: GET /api/dem-shorts/videos/[id]
// Returns a single source video + its speech_segments timeline.
// Segments remain empty until US2 (speaker identification) populates them.
import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

function runPython(script: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", ["-c", script], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT },
    });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { err += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) resolve(out.trim());
      else reject(new Error(err || `exit ${code}`));
    });
  });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!id || !/^[\w-]+$/.test(id)) {
    return NextResponse.json({ error: "invalid video id" }, { status: 400 });
  }

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH

video_id = ${JSON.stringify(id)}

with get_connection(DB_PATH) as conn:
    row = conn.execute(
        "SELECT * FROM source_videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    if not row:
        print(json.dumps({"error": "not_found"}))
        sys.exit(0)
    video = dict(row)
    segs = conn.execute(
        """
        SELECT s.id, s.start_sec, s.end_sec, s.confidence, s.stt_text,
               s.recommendation_score, s.emotion_strength, s.issue_keywords,
               s.is_solo, s.has_profanity, s.politician_id,
               p.name AS politician_name, p.photo_url AS politician_photo
        FROM speech_segments s
        LEFT JOIN politicians p ON p.id = s.politician_id
        WHERE s.source_video_id = ?
        ORDER BY s.start_sec ASC
        """,
        (video_id,),
    ).fetchall()
    segments = [dict(s) for s in segs]

print(json.dumps({"video": video, "segments": segments}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    if (data.error === "not_found") {
      return NextResponse.json({ error: "video not found" }, { status: 404 });
    }
    if ("error" in data) {
      return NextResponse.json({ error: data.error }, { status: 500 });
    }
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 조회 실패" },
      { status: 500 }
    );
  }
}
