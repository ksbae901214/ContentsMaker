import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";
import { writeFileSync, unlinkSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { randomUUID } from "crypto";

export async function POST(req: NextRequest) {
  const tmpInput = join(tmpdir(), `proj_save_${randomUUID()}.json`);
  const tmpScript = join(tmpdir(), `proj_save_${randomUUID()}.py`);

  try {
    const body = await req.json();
    const { name, script_path, image_paths, audio_path, output_path, project_id } = body;

    if (!name || !script_path) {
      return NextResponse.json(
        { error: "name and script_path are required" },
        { status: 400 }
      );
    }

    const inputData = {
      name,
      script_path,
      image_paths: image_paths || null,
      audio_path: audio_path || null,
      output_path: output_path || null,
      project_id: project_id || null,
    };

    writeFileSync(tmpInput, JSON.stringify(inputData), "utf-8");

    const pyCode = `
import json
from pathlib import Path
from src.editor.project import save_project

data = json.loads(Path("${tmpInput}").read_text())

img = None
if data.get("image_paths"):
    img = {int(k): v for k, v in data["image_paths"].items()}

p = save_project(
    name=data["name"],
    script_path=data["script_path"],
    image_paths=img,
    audio_path=data.get("audio_path"),
    output_path=data.get("output_path"),
    project_id=data.get("project_id"),
)
print(json.dumps({"project_id": p.id, "saved_at": p.updated_at}))
`;

    writeFileSync(tmpScript, pyCode, "utf-8");

    const cwd = process.cwd();
    const result = execSync(`python3 ${tmpScript}`, {
      encoding: "utf-8",
      timeout: 10000,
      cwd,
      env: { ...process.env, PYTHONPATH: cwd },
    });

    return NextResponse.json(JSON.parse(result.trim()));
  } catch (e: any) {
    const msg = e.stderr?.toString().slice(-300) || e.message || "Save failed";
    return NextResponse.json({ error: msg }, { status: 500 });
  } finally {
    try { unlinkSync(tmpInput); } catch {}
    try { unlinkSync(tmpScript); } catch {}
  }
}
