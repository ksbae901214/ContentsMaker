import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function PUT(req: NextRequest) {
  try {
    const { scene_id, subtitle_style, script_path, apply_all } =
      await req.json();

    if (!script_path) {
      return NextResponse.json(
        { error: "script_path is required" },
        { status: 400 }
      );
    }
    if (!subtitle_style) {
      return NextResponse.json(
        { error: "subtitle_style is required" },
        { status: 400 }
      );
    }

    const pyCode = `
import json, sys
from pathlib import Path

script_path = ${JSON.stringify(script_path)}
scene_id = ${scene_id ?? "None"}
apply_all = ${apply_all ? "True" : "False"}
style = json.loads(${JSON.stringify(JSON.stringify(subtitle_style))})

path = Path(script_path)
data = json.loads(path.read_text(encoding="utf-8"))

if apply_all:
    for scene in data["scenes"]:
        scene["subtitle_style"] = style
else:
    for scene in data["scenes"]:
        if scene["id"] == scene_id:
            scene["subtitle_style"] = style
            break
    else:
        print(json.dumps({"error": f"Scene {scene_id} not found"}))
        sys.exit(1)

path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"scenes": data["scenes"], "script_path": str(path)}))
`;

    const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      timeout: 10000,
    });

    const parsed = JSON.parse(result.trim());
    if (parsed.error) {
      return NextResponse.json({ error: parsed.error }, { status: 400 });
    }

    return NextResponse.json(parsed);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "Style update failed" },
      { status: 500 }
    );
  }
}
