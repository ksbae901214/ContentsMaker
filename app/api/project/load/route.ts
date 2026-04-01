import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function GET(req: NextRequest) {
  try {
    const id = req.nextUrl.searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }

    const pyCode = `
import json
from src.editor.project import load_project, ProjectError
try:
    p = load_project(${JSON.stringify(id)})
    print(json.dumps({"project": p.to_dict()}))
except ProjectError as e:
    print(json.dumps({"error": str(e)}))
`;

    const result = execSync(`python3 -c ${JSON.stringify(pyCode)}`, {
      encoding: "utf-8",
      timeout: 10000,
      cwd: process.cwd(),
    });

    const parsed = JSON.parse(result.trim());
    if (parsed.error) {
      return NextResponse.json({ error: parsed.error }, { status: 404 });
    }
    return NextResponse.json(parsed);
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
