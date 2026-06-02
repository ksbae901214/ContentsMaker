import { NextRequest } from "next/server";
import { execSync } from "child_process";

export async function POST(req: NextRequest) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const send = (type: string, data: Record<string, unknown>) => {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type, ...data })}\n\n`)
        );
      };

      try {
        const { scene_id, prompt, source_image, resolution, duration } =
          await req.json();

        if (!prompt) {
          send("error", { message: "prompt is required" });
          controller.close();
          return;
        }

        send("progress", {
          scene_id,
          status: "estimating",
          message: "비용 계산 중...",
        });

        // Estimate cost
        const costPy = `
from src.video_gen.factory import create_generator
gen = create_generator()
cost = gen.estimate_cost(duration=${duration || 5}, resolution=${JSON.stringify(resolution || "720p")})
print(f"{cost:.4f}")
`;
        const costStr = execSync(`python3 -c ${JSON.stringify(costPy)}`, {
          encoding: "utf-8",
          timeout: 5000,
          cwd: process.cwd(),
        }).trim();

        send("progress", {
          scene_id,
          status: "cost_estimate",
          cost_usd: parseFloat(costStr),
          message: `예상 비용: $${costStr}`,
        });

        send("progress", {
          scene_id,
          status: "generating",
          message: "AI 영상 생성 시작...",
        });

        // Attempt generation (will fail gracefully if no API key)
        const genPy = `
import asyncio, json
from src.video_gen.factory import create_generator
from src.video_gen.seedance_gen import SeedanceError

async def run():
    gen = create_generator()
    try:
        task_id = await gen.generate(
            prompt=${JSON.stringify(prompt)},
            duration=${duration || 5},
            resolution=${JSON.stringify(resolution || "720p")},
            source_image=${source_image ? JSON.stringify(source_image) : "None"},
        )
        print(json.dumps({"task_id": task_id}))
    except SeedanceError as e:
        print(json.dumps({"error": str(e)}))

asyncio.run(run())
`;
        const genResult = execSync(`python3 -c ${JSON.stringify(genPy)}`, {
          encoding: "utf-8",
          timeout: 30000,
          cwd: process.cwd(),
        }).trim();

        const parsed = JSON.parse(genResult);
        if (parsed.error) {
          send("error", {
            scene_id,
            message: parsed.error,
          });
        } else {
          send("complete", {
            scene_id,
            task_id: parsed.task_id,
          });
        }
      } catch (e: any) {
        send("error", { message: e.message || "Video generation failed" });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
