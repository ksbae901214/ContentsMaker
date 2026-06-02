import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function POST(req: NextRequest) {
  try {
    const { scene_id_1, scene_id_2, script_path } = await req.json();

    if (!scene_id_1 || !scene_id_2 || !script_path) {
      return NextResponse.json(
        { error: "scene_id_1, scene_id_2, script_path are required" },
        { status: 400 }
      );
    }

    const result = execSync(
      `python3 -c "
import json, sys
sys.path.insert(0, '.')
from src.analyzer.script_models import ShortsScript
from src.editor.scene_ops import scene_merge, update_script_file

script = ShortsScript.load('${script_path}')
updated = scene_merge(script, ${scene_id_1}, ${scene_id_2})
path = update_script_file(updated, '${script_path}')
print(json.dumps({'scene': updated.scenes[${scene_id_1} - 1].to_dict(), 'script_path': path}, ensure_ascii=False))
"`,
      { encoding: "utf-8", timeout: 10000 }
    );

    return NextResponse.json(JSON.parse(result.trim()));
  } catch (error: unknown) {
    const message =
      error instanceof Error ? error.message : "씬 병합 실패";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
