// T100: GET /api/dem-shorts/election — 현재 선거 상태 + D-day (FR-030)
import { NextResponse } from "next/server";
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

export async function GET() {
  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.compliance.election_guard import get_election_status

r = get_election_status()
out = {
  "in_election_period": r.in_election_period,
  "next_election": (
      None if r.next_election_date is None else {
          "type": r.next_election_type,
          "date": r.next_election_date.isoformat(),
          "days_until": r.days_until,
          "guard_threshold_days": r.guard_threshold_days,
      }
  ),
  "neutral_mode_enforced": r.in_election_period,
}
print(json.dumps(out, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    return NextResponse.json(data);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "선거 상태 조회 실패";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
