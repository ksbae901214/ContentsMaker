// T115: GET /api/dem-shorts/reports — 월간 편향 리포트 (FR-038)
// Query: month (옵션, YYYY-MM 또는 YYYY-MM-DD, 기본=지난달)
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

const MONTH_RE = /^\d{4}-\d{2}(-\d{2})?$/;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const monthRaw = searchParams.get("month") || "";
  const month = MONTH_RE.test(monthRaw) ? monthRaw : "";

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from datetime import date
from src.dem_shorts.bias_report import generate_bias_report, resolve_previous_month
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH

raw = ${JSON.stringify(month)}
if raw:
    parts = raw.split("-")
    if len(parts) == 2:
        target = date(int(parts[0]), int(parts[1]), 1)
    else:
        target = date.fromisoformat(raw).replace(day=1)
else:
    target = resolve_previous_month()

with get_connection(DB_PATH) as conn:
    # 저장된 리포트가 있으면 사용, 없으면 즉시 계산 (persist 없이)
    row = conn.execute(
        "SELECT * FROM bias_reports WHERE month=?", (target.isoformat(),)
    ).fetchone()
    if row:
        d = dict(row)
        payload = {
            "id": d["id"],
            "month": d["month"],
            "total_uploads": d["total_uploads"],
            "person_shares": json.loads(d.get("person_shares") or "{}"),
            "party_shares": json.loads(d.get("party_shares") or "{}"),
            "template_usage": json.loads(d.get("template_usage") or "{}"),
            "avg_risk_score": d["avg_risk_score"],
            "top_n_person_warning": json.loads(d.get("top_n_person_warning") or "[]"),
            "recommendations": json.loads(d.get("recommendations") or "[]"),
            "generated_at": d["generated_at"],
            "persisted": True,
        }
    else:
        report = generate_bias_report(conn, month=target, persist=False)
        payload = report.to_dict()
        payload["persisted"] = False

print(json.dumps(payload, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    return NextResponse.json(data);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "리포트 조회 실패";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
