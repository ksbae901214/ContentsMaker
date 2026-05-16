import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

const ROOT = process.cwd();

function runPython(script: string): Promise<string> {
  return new Promise((res, rej) => {
    const proc = spawn("python3", ["-c", script], {
      cwd: ROOT,
      env: { ...process.env, PYTHONPATH: ROOT },
    });
    let out = "";
    let err = "";
    proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { err += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) res(out.trim());
      else rej(new Error(err || `exit ${code}`));
    });
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  if (!body || !body.name || !Array.isArray(body.titles) || body.titles.length === 0) {
    return NextResponse.json(
      { error: "name과 titles 배열이 필요합니다", ideas: [] },
      { status: 400 }
    );
  }

  const safeName = String(body.name).replace(/['"\\]/g, "");
  const safeTitles = (body.titles as string[])
    .map((t) => String(t).replace(/['"\\]/g, ""))
    .slice(0, 20);
  const maxIdeas = Math.min(parseInt(String(body.maxIdeas || "5"), 10), 10);

  const pyScript = `
import json, sys
sys.path.insert(0, ${JSON.stringify(ROOT)})
from src.analyzer.idea_generator import generate_video_ideas
from src.analyzer.claude_analyzer import AnalyzerError

try:
    ideas = generate_video_ideas(
        ${JSON.stringify(safeName)},
        ${JSON.stringify(safeTitles)},
        ${maxIdeas},
    )
    result = [
        {"title": i.title, "hook": i.hook, "angle": i.angle, "natvKeywords": i.natv_keywords}
        for i in ideas
    ]
    print(json.dumps({"ideas": result}, ensure_ascii=False))
except AnalyzerError as e:
    print(json.dumps({"error": str(e), "ideas": []}))
`;

  try {
    const output = await runPython(pyScript);
    const data = JSON.parse(output);
    return NextResponse.json(data);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "아이디어 생성 실패", ideas: [] },
      { status: 200 }
    );
  }
}
