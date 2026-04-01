import { NextResponse } from "next/server";
import { execSync } from "child_process";

export async function GET() {
  try {
    const pyCode = `
import json
from src.editor.project import list_projects
print(json.dumps({"projects": list_projects()}))
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
