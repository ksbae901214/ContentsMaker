// T088: POST /api/dem-shorts/drafts — 쇼츠 초안 생성 (US3 시작)
import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

function runPython(script: string, stdin?: string): Promise<string> {
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
    if (stdin) proc.stdin.write(stdin);
    proc.stdin.end();
  });
}

export async function POST(request: NextRequest) {
  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH
from src.dem_shorts.drafts_repo import create_draft, DraftError

data = json.loads(sys.stdin.read())
try:
    with get_connection(DB_PATH) as conn:
        draft = create_draft(conn, data)
    print(json.dumps({"draft": draft}, ensure_ascii=False, default=str))
except DraftError as e:
    msg = str(e)
    code = 404 if "segment_not_found" in msg else 400
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript, JSON.stringify(body));
    const data = JSON.parse(output);
    if (data.error) {
      const status = data.code === 404 ? 404 : data.code === 500 ? 500 : 400;
      return NextResponse.json({ error: data.error }, { status });
    }
    return NextResponse.json(data.draft, { status: 201 });
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "draft 생성 실패" }, { status: 500 });
  }
}
