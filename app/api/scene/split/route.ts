import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function POST(req: NextRequest) {
  try {
    const { scene_id, split_position, script_path } = await req.json();

    if (!scene_id || split_position == null || !script_path) {
      return NextResponse.json(
        { error: "scene_id, split_position, script_path are required" },
        { status: 400 }
      );
    }

    const result = execSync(
      `python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.analyzer.script_models import ShortsScript
from src.editor.scene_ops import scene_split, update_script_file

script = ShortsScript.load('${script_path}')
updated = scene_split(script, ${scene_id}, ${split_position})
path = update_script_file(updated, '${script_path}')
print(json.dumps({'scenes': [s.to_dict() for s in updated.scenes], 'script_path': path}, ensure_ascii=False))
"`,
      { encoding: "utf-8", timeout: 10000 }
    );

    return NextResponse.json(JSON.parse(result.trim()));
  } catch (error: unknown) {
    const message =
      error instanceof Error ? error.message : "씬 분할 실패";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
