// T059: PATCH/DELETE /api/dem-shorts/whitelist/[id]
// 정치인 등급·카테고리·활성 변경, 삭제.
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
    if (stdin) {
      proc.stdin.write(stdin);
    }
    proc.stdin.end();
  });
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const pid = parseInt(id, 10);
  if (!Number.isFinite(pid) || pid <= 0) {
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
from src.dem_shorts.whitelist_repo import update_politician, WhitelistError

patch = json.loads(sys.stdin.read())
try:
    with get_connection(DB_PATH) as conn:
        p = update_politician(conn, ${pid}, patch)
    print(json.dumps({"politician": p}, ensure_ascii=False, default=str))
except WhitelistError as e:
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
      const status = data.code === 404 ? 404 : data.code === 500 ? 500 : 400;
      return NextResponse.json({ error: data.error }, { status });
    }
    return NextResponse.json(data.politician);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 업데이트 실패" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const pid = parseInt(id, 10);
  if (!Number.isFinite(pid) || pid <= 0) {
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH
from src.dem_shorts.whitelist_repo import delete_politician, WhitelistError

try:
    with get_connection(DB_PATH) as conn:
        delete_politician(conn, ${pid})
    print(json.dumps({"deleted": True}))
except WhitelistError as e:
    msg = str(e)
    code = 404 if "not_found" in msg.lower() else 400
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    if (data.error) {
      const status = data.code === 404 ? 404 : data.code === 500 ? 500 : 400;
      return NextResponse.json({ error: data.error }, { status });
    }
    return NextResponse.json({ deleted: true });
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 삭제 실패" },
      { status: 500 }
    );
  }
}
