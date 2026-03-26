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

    const pyCode = `
import json
from src.editor.project import save_project

p = save_project(
    name=${JSON.stringify(name)},
    script_path=${JSON.stringify(script_path)},
    image_paths=${image_paths ? JSON.stringify(image_paths) : "None"},
    audio_path=${audio_path ? JSON.stringify(audio_path) : "None"},
    output_path=${output_path ? JSON.stringify(output_path) : "None"},
    project_id=${project_id ? JSON.stringify(project_id) : "None"},
)
print(json.dumps({"project_id": p.id, "saved_at": p.updated_at}))
`;

    const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      timeout: 10000,
      cwd: process.cwd(),
    });

    return NextResponse.json(JSON.parse(result.trim()));
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
