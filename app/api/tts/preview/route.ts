import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";
import { readFileSync, unlinkSync, existsSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { randomUUID } from "crypto";

const DEFAULT_SAMPLE = "안녕하세요, 이 음성은 미리듣기 샘플입니다.";

export async function POST(req: NextRequest) {
  const tmpPath = join(tmpdir(), `tts_preview_${randomUUID()}.mp3`);

  try {
    const { voice, text } = await req.json();

    if (!voice) {
      return NextResponse.json(
        { error: "voice is required" },
        { status: 400 }
      );
    }

    const sampleText = (text || DEFAULT_SAMPLE).slice(0, 100);

    const pyCode = `
import asyncio
import edge_tts

async def gen():
    c = edge_tts.Communicate(
        text=${JSON.stringify(sampleText)},
        voice=${JSON.stringify(voice)},
        rate="+0%",
        pitch="+0Hz",
    )
    await c.save(${JSON.stringify(tmpPath)})

asyncio.run(gen())
print("OK")
`;

    execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      timeout: 15000,
    });

    if (!existsSync(tmpPath)) {
      return NextResponse.json(
        { error: "Failed to generate preview" },
        { status: 500 }
      );
    }

    const audioData = readFileSync(tmpPath);

    return new NextResponse(audioData, {
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": String(audioData.length),
        "Cache-Control": "public, max-age=3600",
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      { error: e.message || "Preview generation failed" },
      { status: 500 }
    );
  } finally {
    try {
      if (existsSync(tmpPath)) unlinkSync(tmpPath);
    } catch {
      // cleanup best-effort
    }
  }
}
