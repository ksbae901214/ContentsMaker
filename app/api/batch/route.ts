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
        const { items, template } = await req.json();

        if (!items || !Array.isArray(items) || items.length === 0) {
          send("error", { message: "items array is required" });
          controller.close();
          return;
        }

        send("progress", {
          message: `${items.length}개 작업 시작...`,
          total: items.length,
          completed: 0,
        });

        for (let i = 0; i < items.length; i++) {
          const item = items[i];
          send("job_update", {
            job_index: i,
            status: "processing",
            message: `작업 ${i + 1}/${items.length} 처리 중...`,
          });

          try {
            // Process each item through the pipeline
            const pyCode = `
import json, sys
from pathlib import Path

item = json.loads(${JSON.stringify(JSON.stringify(item))})
input_type = item.get("input_type", "text")
input_data = item.get("input_data", "")

if input_type == "url":
    from src.scraper.url_scraper import extract_from_url
    from src.analyzer.claude_analyzer import analyze
    post = extract_from_url(input_data)
    script = analyze(post)
elif input_type == "file":
    from src.scraper.models import BlindPost
    from src.analyzer.claude_analyzer import analyze
    data = json.loads(Path(input_data).read_text(encoding="utf-8"))
    post = BlindPost.from_dict(data)
    script = analyze(post)
else:
    print(json.dumps({"error": "Unsupported input_type: " + input_type}))
    sys.exit(0)

# Save script
from src.analyzer.script_models import ShortsScript
script_dict = script.to_dict()
from datetime import datetime
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
safe = "".join(c for c in script.metadata.title[:20] if c.isalnum() or c in " _-").strip().replace(" ", "_")
sp = Path("data/scripts") / f"{ts}_{safe}.json"
sp.parent.mkdir(parents=True, exist_ok=True)
sp.write_text(json.dumps(script_dict, ensure_ascii=False, indent=2))
print(json.dumps({"script_path": str(sp), "title": script.metadata.title}))
`;

            const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
              encoding: "utf-8",
              timeout: 120000,
              cwd: process.cwd(),
            }).trim();

            const parsed = JSON.parse(result);
            if (parsed.error) {
              send("job_update", {
                job_index: i,
                status: "failed",
                error: parsed.error,
              });
            } else {
              send("job_update", {
                job_index: i,
                status: "completed",
                title: parsed.title,
                script_path: parsed.script_path,
              });
            }
          } catch (e: any) {
            send("job_update", {
              job_index: i,
              status: "failed",
              error: e.message?.slice(0, 200) || "Unknown error",
            });
          }
        }

        send("complete", {
          message: `${items.length}개 작업 완료`,
          total: items.length,
        });
      } catch (e: any) {
        send("error", { message: e.message || "Batch failed" });
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
