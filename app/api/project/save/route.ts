import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, script_path, image_paths, audio_path, output_path, project_id } = body;

    if (!name || !script_path) {
      return NextResponse.json(
        { error: "name and script_path are required" },
        { status: 400 }
      );
    }

    const inputData = JSON.stringify({
      name,
      script_path,
      image_paths: image_paths || null,
      audio_path: audio_path || null,
      output_path: output_path || null,
      project_id: project_id || null,
    });

    const pyCode = `
import json, sys

data = json.loads(sys.stdin.read())
from src.editor.project import save_project

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

    const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      input: inputData,
      timeout: 10000,
      cwd: process.cwd(),
    });

    return NextResponse.json(JSON.parse(result.trim()));
  } catch (e: any) {
    const msg = e.stderr?.toString().slice(-300) || e.message || "Save failed";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
