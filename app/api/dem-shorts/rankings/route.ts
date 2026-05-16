// T114: GET /api/dem-shorts/rankings — 주간 여성·청년 정치인 랭킹 (FR-008)
// Query: week_start (옵션, 기본=이번 주 월요일)
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
    proc.stdout.on("data", (d: Buffer) => {
      out += d.toString();
    });
    proc.stderr.on("data", (d: Buffer) => {
      err += d.toString();
    });
    proc.on("close", (code) => {
      if (code === 0) resolve(out.trim());
      else reject(new Error(err || `exit ${code}`));
    });
    proc.stdin.end();
  });
}

const WEEK_START_RE = /^\d{4}-\d{2}-\d{2}$/;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const weekStartRaw = searchParams.get("week_start") || "";
  const weekStart = WEEK_START_RE.test(weekStartRaw) ? weekStartRaw : "";

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.ranking_batch import resolve_week_start
from src.dem_shorts.utils.paths import DB_PATH

week_in = ${JSON.stringify(weekStart)}
if week_in:
    from datetime import date
    week = date.fromisoformat(week_in)
else:
    week = resolve_week_start()

with get_connection(DB_PATH) as conn:
    rows = conn.execute(
        """
        SELECT
          wr.rank, wr.score, wr.delta_vs_prev_week AS delta, wr.tag,
          wr.data_sources,
          p.id            AS politician_id,
          p.name          AS politician_name,
          p.party         AS politician_party,
          p.category      AS politician_category,
          p.tier          AS politician_tier,
          p.photo_url     AS politician_photo_url
        FROM weekly_rankings wr
        JOIN politicians p ON p.id = wr.politician_id
        WHERE wr.week_start = ?
        ORDER BY wr.rank ASC
        """,
        (week.isoformat(),),
    ).fetchall()
out_rows = []
for r in rows:
    d = dict(r)
    try:
        d["data_sources"] = json.loads(d.get("data_sources") or "{}")
    except Exception:
        d["data_sources"] = {}
    out_rows.append({
        "rank": d["rank"],
        "score": d["score"],
        "delta": d["delta"],
        "tag": d["tag"],
        "data_sources": d["data_sources"],
        "politician": {
            "id": d["politician_id"],
            "name": d["politician_name"],
            "party": d["politician_party"],
            "category": d["politician_category"],
            "tier": d["politician_tier"],
            "photo_url": d.get("politician_photo_url"),
        },
    })
print(json.dumps({"week_start": week.isoformat(), "rankings": out_rows}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    return NextResponse.json(data);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "랭킹 조회 실패";
    return NextResponse.json({ error: msg, rankings: [] }, { status: 500 });
  }
}
