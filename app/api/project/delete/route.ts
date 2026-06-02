import { NextRequest, NextResponse } from "next/server";
import { execSync } from "child_process";

export async function DELETE(req: NextRequest) {
  try {
    const id = req.nextUrl.searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }

    const pyCode = `
import json
from src.editor.project import delete_project
deleted = delete_project(${JSON.stringify(id)})
print(json.dumps({"deleted": deleted}))
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
