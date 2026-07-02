import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

// Claude metadata generation ~60s
export const maxDuration = 60;

function runPy(pyCode: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn("python3", ["-c", pyCode], { cwd: ROOT, env: { ...process.env } });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => { out += d; });
    p.stderr.on("data", (d) => { err += d; });
    p.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(err.slice(-1000) || `exit ${code}`));
      } else {
        const lines = out.trim().split("\n");
        resolve(lines[lines.length - 1]);
      }
    });
    p.on("error", (e) => reject(new Error(`Python: ${e.message}`)));
  });
}

/**
 * POST /api/jpolitics/meta
 *
 * Body: { workDir: string, momentIdx: number }
 * Response: { titleCandidates: string[], hashtags: string[], pinnedComment: string }
 */
export async function POST(req: NextRequest) {
  let body: { workDir?: string; momentIdx?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "invalid_request", detail: "JSON body required" },
      { status: 400 },
    );
  }

  const workDir = (body.workDir || "").trim();
  const momentIdx = typeof body.momentIdx === "number" ? body.momentIdx : 1;

  if (!workDir) {
    return NextResponse.json(
      { error: "invalid_request", detail: "workDir required" },
      { status: 400 },
    );
  }

  const pyCode = `
import sys, json
sys.path.insert(0, '${ROOT}')
from pathlib import Path

work_dir = Path(${JSON.stringify(workDir)})
n = ${momentIdx}

moments_json = work_dir / "moments.json"
if not moments_json.exists():
    print(json.dumps({"error": "moments_not_found"}))
    sys.exit(0)

data = json.loads(moments_json.read_text())
moments = data.get("moments", [])
top_sorted = sorted(moments, key=lambda m: m.get("confidence", 0), reverse=True)
if n < 1 or n > len(top_sorted):
    print(json.dumps({"error": "moment_index_out_of_range", "total": len(top_sorted)}))
    sys.exit(0)

moment = top_sorted[n - 1]
video_title = data.get("video_title", "")
channel = data.get("channel", "")
hook = moment.get("hook_question", "")
summary = moment.get("summary", "")
kind = moment.get("kind", "other")
speaker = moment.get("speaker", "")

kind_labels = {
    "laughter": "웃음", "clash": "충돌", "outburst": "언성",
    "gaffe": "실언", "silence": "정적", "other": "모먼트",
}
kind_label = kind_labels.get(kind, "모먼트")

title_candidates = [
    f"[정치 {kind_label}] {hook}" if hook else f"[정치 {kind_label}] {summary[:30]}",
    f"{speaker} {kind_label} 순간" + (f" | {video_title[:20]}" if video_title else "") if speaker else f"{kind_label} 순간 | {video_title[:30]}",
    f"이 장면 실화? {summary[:40]}" if summary else f"{kind_label} 포착 | {channel}",
]
title_candidates = [t.strip() for t in title_candidates if t.strip()]

hashtags = ["#정치쇼츠", "#국회", f"#{kind_label}", "#정치"]
if speaker:
    hashtags.insert(1, f"#{speaker.replace(' ', '')}")
if channel:
    hashtags.append(f"#{channel.replace(' ', '').replace('-', '')[:15]}")

pinned = f"📌 출처: {channel or '국회 영상'} | {video_title or ''}"
if hook:
    pinned += f"\\n🎯 {hook}"

print(json.dumps({
    "titleCandidates": title_candidates[:3],
    "hashtags": list(dict.fromkeys(hashtags))[:8],
    "pinnedComment": pinned.strip(),
}, ensure_ascii=False))
`;

  try {
    const raw = await runPy(pyCode);
    const parsed = JSON.parse(raw);
    if (parsed.error) {
      return NextResponse.json(
        { error: parsed.error, detail: parsed.detail, workDir },
        { status: 400 },
      );
    }
    return NextResponse.json(parsed, { status: 200 });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json(
      { error: "meta_failed", detail: msg.slice(0, 500), workDir },
      { status: 502 },
    );
  }
}
