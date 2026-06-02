// T081: POST /api/dem-shorts/drafts/[id]/gate
// ⭐ 컴플라이언스 게이트 실행 + 결과 저장 (SC-005, FR-025).
// 서버사이드에서만 판정 — 어떤 파라미터로도 우회 불가.
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

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const did = parseInt(id, 10);
  if (!Number.isFinite(did) || did <= 0) {
    return NextResponse.json({ error: "invalid_draft_id" }, { status: 400 });
  }

  let body: any = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  // ⭐ 핵심: 서버가 받아들이는 필드는 manual_fact_check / manual_defamation_check / operator_id 뿐.
  // "skip_gate" 같은 필드는 Python GateContext dataclass가 수용하지 않아 TypeError 발생.
  const manualFactCheck = body.manual_fact_check === true;
  const manualDefamationCheck = body.manual_defamation_check === true;
  const operatorId = (body.operator_id || "owner").toString();

  const gateInput = {
    draft_id: did,
    manual_fact_check_signed_by: manualFactCheck ? operatorId : null,
    manual_defamation_check_signed_by: manualDefamationCheck ? operatorId : null,
    operator_id: operatorId,
  };

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.compliance.gate import GateContext, GateError, validate
from src.dem_shorts.utils.paths import DB_PATH

inp = json.loads(sys.stdin.read())
try:
    ctx = GateContext(
        draft_id=inp['draft_id'],
        manual_fact_check_signed_by=inp['manual_fact_check_signed_by'],
        manual_defamation_check_signed_by=inp['manual_defamation_check_signed_by'],
        operator_id=inp['operator_id'],
        db_path=DB_PATH,
    )
    result = validate(ctx)
    out = result.to_dict()
    out['is_passed'] = result.is_passed()
    print(json.dumps(out, ensure_ascii=False))
except GateError as e:
    print(json.dumps({"error": str(e), "code": 404 if "not_found" in str(e).lower() else 500}))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}))
`;

  try {
    const output = await runPython(pyScript, JSON.stringify(gateInput));
    const data = JSON.parse(output);
    if (data.error) {
      const status = data.code === 404 ? 404 : data.code === 400 ? 400 : 500;
      return NextResponse.json({ error: data.error }, { status });
    }
    // 최종 게이트 상태 반환 — 프론트엔드는 is_passed 값만 신뢰
    const statusCode = data.is_passed ? 200 : 400;
    return NextResponse.json(data, { status: statusCode });
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "gate 실행 실패" },
      { status: 500 }
    );
  }
}
