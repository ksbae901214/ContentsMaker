// T036: GET /api/dem-shorts/videos
// Dashboard source-video list with dem_score ordering (US1, FR-004).
// Reads directly from SQLite `source_videos` table via Python subprocess.
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

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const sinceHours = Math.max(1, Math.min(parseInt(searchParams.get("since_hours") || "24", 10), 720));
  const minScore = Math.max(0, parseFloat(searchParams.get("min_score") || "0"));
  const sessionType = searchParams.get("session_type") || "";
  const includeExcluded = searchParams.get("include_excluded") === "true";
  const limit = Math.min(parseInt(searchParams.get("limit") || "50", 10), 200);

  const allowedSessions = ["", "plenary", "committee", "audit", "hearing", "press", "other"];
  const safeSession = allowedSessions.includes(sessionType) ? sessionType : "";

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from datetime import datetime, timedelta, timezone
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH

since = (datetime.now(timezone.utc) - timedelta(hours=${sinceHours})).isoformat()
params = [since]

query = """
  SELECT video_id, title, description, published_at, duration_sec,
         thumbnail_url, session_type, dem_score, stt_status, status,
         excluded_reason, created_at, updated_at
  FROM source_videos
  WHERE published_at >= ?
    AND dem_score >= ${minScore}
"""
if not ${includeExcluded ? "True" : "False"}:
    query += " AND status != 'excluded'"
if ${JSON.stringify(safeSession)}:
    query += " AND session_type = ?"
    params.append(${JSON.stringify(safeSession)})
query += " ORDER BY dem_score DESC, published_at DESC LIMIT ${limit}"

try:
    with get_connection(DB_PATH) as conn:
        rows = conn.execute(query, params).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM source_videos WHERE published_at >= ?", (since,)
        ).fetchone()[0]
    videos = [dict(r) for r in rows]
    print(json.dumps({"videos": videos, "total": total}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "videos": []}))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    if ("error" in data && !data.videos) {
      return NextResponse.json({ error: data.error, videos: [], total: 0 }, { status: 500 });
    }
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 조회 실패", videos: [], total: 0 },
      { status: 500 }
    );
  }
}
