// T089: GET/PATCH /api/dem-shorts/drafts/[id]
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

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const did = parseInt(id, 10);
  if (!Number.isFinite(did) || did <= 0) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH
from src.dem_shorts.drafts_repo import get_draft

try:
    with get_connection(DB_PATH) as conn:
        d = get_draft(conn, ${did})
    if d is None:
        print(json.dumps({"error": "not_found", "code": 404}))
    else:
        print(json.dumps({"draft": d}, ensure_ascii=False, default=str))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;
  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: data.code || 500 });
    }
    return NextResponse.json(data.draft);
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "조회 실패" }, { status: 500 });
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const did = parseInt(id, 10);
  if (!Number.isFinite(did) || did <= 0) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
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
from src.dem_shorts.drafts_repo import update_draft, DraftError

patch = json.loads(sys.stdin.read())
try:
    with get_connection(DB_PATH) as conn:
        d = update_draft(conn, ${did}, patch)
    print(json.dumps({"draft": d}, ensure_ascii=False, default=str))
except DraftError as e:
    msg = str(e)
    code = 404 if "not_found" in msg.lower() else 400
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;
  try {
    const output = await runPython(pyScript, JSON.stringify(body));
    const data = JSON.parse(output);
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: data.code || 500 });
    }
    return NextResponse.json(data.draft);
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "업데이트 실패" }, { status: 500 });
  }
}
