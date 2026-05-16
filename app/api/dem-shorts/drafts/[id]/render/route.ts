// T084: POST /api/dem-shorts/drafts/[id]/render
// SSE 진행 스트림 + ⭐ 게이트 통과 재확인 (이중 방어, SC-005).
import { NextRequest } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const did = parseInt(id, 10);
  if (!Number.isFinite(did) || did <= 0) {
    return new Response(JSON.stringify({ error: "invalid_draft_id" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ⭐ STEP 1: 게이트 통과 재확인 (서버사이드에서만 결정, SC-005)
  const verifyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.renderer import verify_gate_passed, RenderError

try:
    verify_gate_passed(${did})
    print(json.dumps({"ok": True}))
except RenderError as e:
    print(json.dumps({"ok": False, "error": str(e)}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
`;

  const verifyOutput = await new Promise<string>((resolve, reject) => {
    const proc = spawn("python3", ["-c", verifyScript], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT },
    });
    let out = "";
    proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) resolve(out.trim());
      else reject(new Error(`exit ${code}`));
    });
    proc.stdin.end();
  });

  try {
    const data = JSON.parse(verifyOutput);
    if (!data.ok) {
      // ⭐ 게이트 미통과 → 403 (FR-025 이중 방어)
      return new Response(
        JSON.stringify({ error: "gate_not_passed", detail: data.error }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      );
    }
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: "gate_verification_failed", detail: e.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  // STEP 2: SSE 스트림 시작 + 실제 렌더링
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const emit = (obj: any) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));
      };

      emit({ type: "progress", stage: "gate_verified", pct: 5 });

      const renderScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.dem_shorts.renderer import render_draft, RenderError

try:
    result = render_draft(${did})
    print(json.dumps({
        "ok": True,
        "rendered_path": str(result.rendered_path),
        "duration_sec": result.duration_sec,
        "used_cache": result.used_cache,
        "cache_key": result.cache_key,
    }, ensure_ascii=False))
except RenderError as e:
    print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
`;

      const proc = spawn("python3", ["-c", renderScript], {
        cwd: ROOT,
        env: { ...process.env, PYTHONPATH: ROOT },
      });

      let out = "";
      proc.stdout.on("data", (d: Buffer) => {
        out += d.toString();
        // Heuristic progress based on stdout content (renderer uses logging)
        emit({ type: "progress", stage: "rendering", pct: 50 });
      });
      proc.stderr.on("data", (_d: Buffer) => {
        // Remotion writes progress logs to stderr — forward coarse status
        emit({ type: "progress", stage: "encoding", pct: 75 });
      });

      await new Promise<void>((resolve) => {
        proc.on("close", () => resolve());
        proc.stdin.end();
      });

      try {
        const data = JSON.parse(out.trim());
        if (data.ok) {
          emit({
            type: "done",
            rendered_path: data.rendered_path,
            duration_sec: data.duration_sec,
            used_cache: data.used_cache,
          });
        } else {
          emit({ type: "error", error: data.error });
        }
      } catch (e: any) {
        emit({ type: "error", error: `render output parse failed: ${e.message}` });
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
