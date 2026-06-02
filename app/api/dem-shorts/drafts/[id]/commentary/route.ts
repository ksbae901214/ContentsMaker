// T090: POST /api/dem-shorts/drafts/[id]/commentary — AI 후보 3개 생성 (FR-020)
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
    return NextResponse.json({ error: "invalid_id" }, { status: 400 });
  }
  let body: any = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const maxChars = Math.max(5, Math.min(30, parseInt(body.max_chars_per_candidate || "15", 10)));
  const toneHint = (body.tone_hint || "팩트 기반 객관적").toString();

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.db import get_connection
from src.dem_shorts.utils.paths import DB_PATH
from src.dem_shorts.editor.commentary_gen import (
    CommentaryContext, CommentaryGenError, generate_commentary_candidates
)
from src.dem_shorts.compliance.election_guard import is_in_election_period

inp = json.loads(sys.stdin.read())
try:
    with get_connection(DB_PATH) as conn:
        draft = conn.execute("SELECT * FROM shorts_drafts WHERE id=?", (${did},)).fetchone()
        if not draft:
            print(json.dumps({"error": "draft_not_found", "code": 404}))
            sys.exit(0)
        segment = conn.execute(
            "SELECT * FROM speech_segments WHERE id=?", (draft["segment_id"],)
        ).fetchone()
        politician = None
        if segment and segment["politician_id"]:
            politician = conn.execute(
                "SELECT * FROM politicians WHERE id=?", (segment["politician_id"],)
            ).fetchone()
        source_video = conn.execute(
            "SELECT * FROM source_videos WHERE video_id=?", (segment["source_video_id"],)
        ).fetchone() if segment else None

    ctx = CommentaryContext(
        politician_name=politician["name"] if politician else "(미식별)",
        stt_text=segment["stt_text"] if segment else "",
        tone_guide=politician["tone_guide"] if politician else "",
        tone_hint=inp["tone_hint"],
        session_type=source_video["session_type"] if source_video else "",
        is_election_period=is_in_election_period(),
    )
    candidates = generate_commentary_candidates(ctx, max_chars=inp["max_chars"])
    print(json.dumps({"candidates": candidates}, ensure_ascii=False))
except CommentaryGenError as e:
    print(json.dumps({"error": str(e), "code": 502}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e), "code": 500}, ensure_ascii=False))
`;

  try {
    const output = await runPython(pyScript, JSON.stringify({
      tone_hint: toneHint,
      max_chars: maxChars,
    }));
    const data = JSON.parse(output);
    if (data.error) {
      return NextResponse.json({ error: data.error }, { status: data.code || 500 });
    }
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json({ error: e.message || "해설 생성 실패" }, { status: 500 });
  }
}
