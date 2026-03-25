import { NextRequest, NextResponse } from "next/server";
import { readFile, writeFile } from "fs/promises";
import { resolve } from "path";

const ROOT = process.cwd();
const ALLOWED_DIR = resolve(ROOT, "data", "scripts");

function isAllowedPath(p: string): boolean {
  const resolved = resolve(p);
  return resolved.startsWith(ALLOWED_DIR);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as {
      scriptPath: string;
      sceneId?: number;
      text?: string;
      voiceText?: string;
      title?: string;
    };
    const { scriptPath, sceneId, text, voiceText, title } = body;

    if (!scriptPath) {
      return NextResponse.json({ error: "scriptPath required" }, { status: 400 });
    }

    if (!isAllowedPath(scriptPath)) {
      return NextResponse.json({ error: "허용되지 않는 경로" }, { status: 403 });
    }

    const raw = await readFile(scriptPath, "utf-8");
    const script = JSON.parse(raw);

    // Title update mode
    if (title !== undefined) {
      const updatedScript = {
        ...script,
        metadata: { ...script.metadata, title },
      };
      await writeFile(scriptPath, JSON.stringify(updatedScript, null, 2), "utf-8");
      return NextResponse.json({ success: true, title });
    }

    // Scene text update mode
    if (!Number.isInteger(sceneId) || text === undefined) {
      return NextResponse.json({ error: "sceneId and text required" }, { status: 400 });
    }

    const updatedScenes = script.scenes.map((s: any) => {
      if (s.id !== sceneId) return s;
      return { ...s, text, voice_text: voiceText || text };
    });

    const ttsScript = updatedScenes.map((s: any) => s.voice_text).join(" ");

    const updatedScript = {
      ...script,
      scenes: updatedScenes,
      audio: { ...script.audio, tts_script: ttsScript },
    };

    await writeFile(scriptPath, JSON.stringify(updatedScript, null, 2), "utf-8");

    return NextResponse.json({
      success: true,
      scene: updatedScenes.find((s: any) => s.id === sceneId),
    });
  } catch (e: any) {
    return NextResponse.json({ error: "스크립트 수정 실패" }, { status: 500 });
  }
}
