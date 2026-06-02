import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function POST(req: NextRequest) {
  try {
    const { scenes, target_language } = await req.json();

    if (!scenes || !Array.isArray(scenes)) {
      return NextResponse.json(
        { error: "scenes array is required" },
        { status: 400 }
      );
    }
    if (!target_language || !["en", "ja"].includes(target_language)) {
      return NextResponse.json(
        { error: 'target_language must be "en" or "ja"' },
        { status: 400 }
      );
    }

    const pyCode = `
import json
from src.editor.translator import translate_subtitles, TranslationError

scenes = json.loads(${JSON.stringify(JSON.stringify(scenes))})
try:
    result = translate_subtitles(scenes, ${JSON.stringify(target_language)})
    print(json.dumps({"translations": result}))
except TranslationError as e:
    print(json.dumps({"error": str(e)}))
`;

    const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      timeout: 30000,
      cwd: process.cwd(),
    });

    const parsed = JSON.parse(result.trim());
    if (parsed.error) {
      return NextResponse.json({ error: parsed.error }, { status: 400 });
    }

    return NextResponse.json(parsed);
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "Translation failed" },
      { status: 500 }
    );
  }
}
