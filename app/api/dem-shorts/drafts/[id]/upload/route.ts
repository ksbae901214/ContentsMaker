// T087: POST /api/dem-shorts/drafts/[id]/upload
// ⭐ 운영자 확정 + 게이트 재확인 이중 방어 (FR-036, FR-037, SC-005).
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

  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  // ⭐ operator_confirmed 필수 (FR-037)
  if (body.operator_confirmed !== true) {
    return NextResponse.json(
      { error: "operator_not_confirmed", detail: "운영자가 최종 확정해야 업로드 가능합니다" },
      { status: 403 }
    );
  }

  const uploadInput = {
    draft_id: did,
    title: (body.title || "").toString(),
    description: (body.description || "").toString(),
    tags: Array.isArray(body.tags) ? body.tags.map((t: any) => t.toString()) : [],
    scheduled_publish_at: body.scheduled_publish_at || null,
    operator_confirmed: true,
    dry_run: body.dry_run === true,
  };

  const pyScript = `
import json, sys
from datetime import datetime
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.uploader import UploadRequest, UploadError, upload

inp = json.loads(sys.stdin.read())
sched = None
if inp.get("scheduled_publish_at"):
    try:
        sched = datetime.fromisoformat(inp["scheduled_publish_at"].replace("Z", "+00:00"))
    except Exception:
        print(json.dumps({"error": "invalid_scheduled_publish_at_format", "code": 400}))
        sys.exit(0)

req = UploadRequest(
    draft_id=inp["draft_id"],
    title=inp["title"],
    description=inp["description"],
    tags=tuple(inp["tags"]),
    scheduled_publish_at=sched,
    operator_confirmed=inp["operator_confirmed"],
)
try:
    result = upload(req, dry_run=inp.get("dry_run", False))
    print(json.dumps({
        "youtube_video_id": result.youtube_video_id,
        "youtube_url": result.youtube_url,
        "uploaded_shorts_id": result.uploaded_shorts_id,
        "scheduled_publish_at": result.scheduled_publish_at.isoformat() if result.scheduled_publish_at else None,
    }, ensure_ascii=False))
except UploadError as e:
    msg = str(e)
    code = 403 if ("gate_not_passed" in msg or "operator" in msg or "natv" in msg or "fact_links" in msg) else 400
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript, JSON.stringify(uploadInput));
    const data = JSON.parse(output);
    if (data.error) {
      const status = data.code === 403 ? 403 : data.code === 500 ? 500 : 400;
      return NextResponse.json({ error: data.error }, { status });
    }
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "업로드 실패" },
      { status: 500 }
    );
  }
}
