// T058: GET/POST /api/dem-shorts/whitelist (FR-007)
// Whitelist 정치인 목록 조회 + 추가. tier='auto' 직접 등록 차단.
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
      proc.stdin.end();
    } else {
      proc.stdin.end();
    }
  });
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tier = searchParams.get("tier") || "";
  const category = searchParams.get("category") || "";
  const active = searchParams.get("active");

  const allowedTiers = ["", "pinned", "auto", "pending", "blocked"];
  const allowedCategories = ["", "fixed", "female", "youth", "alliance"];
  const safeTier = allowedTiers.includes(tier) ? tier : "";
  const safeCategory = allowedCategories.includes(category) ? category : "";
  const activeParam = active === "true" ? "True" : active === "false" ? "False" : "None";

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH
from src.dem_shorts.whitelist_repo import list_politicians

try:
    with get_connection(DB_PATH) as conn:
        rows = list_politicians(
            conn,
            tier=${safeTier ? JSON.stringify(safeTier) : "None"},
            category=${safeCategory ? JSON.stringify(safeCategory) : "None"},
            active=${activeParam},
        )
    print(json.dumps({"politicians": rows}, ensure_ascii=False, default=str))
except Exception as e:
    print(json.dumps({"error": str(e), "politicians": []}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    if (data.error) {
      return NextResponse.json(data, { status: 400 });
    }
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 조회 실패", politicians: [] },
      { status: 500 }
    );
  }
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
from src.dem_shorts.whitelist_repo import create_politician, WhitelistError

data = json.loads(sys.stdin.read())
try:
    with get_connection(DB_PATH) as conn:
        p = create_politician(conn, data)
    print(json.dumps({"politician": p}, ensure_ascii=False, default=str))
except WhitelistError as e:
    msg = str(e)
    code = 409 if "already_exists" in msg else 400
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript, JSON.stringify(body));
    const data = JSON.parse(output);
    if (data.error) {
      const status = data.code === 409 ? 409 : data.code === 500 ? 500 : 400;
      return NextResponse.json({ error: data.error }, { status });
    }
    return NextResponse.json(data.politician, { status: 201 });
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "DB 쓰기 실패" },
      { status: 500 }
    );
  }
}
