import { NextResponse } from "next/server";

import { getDirectoryServiceTypeCounts } from "@/lib/directory-db";

export const runtime = "nodejs";

export async function GET() {
  try {
    const serviceTypes = await getDirectoryServiceTypeCounts();
    return NextResponse.json({
      data: serviceTypes,
      meta: { source: "database" },
    });
  } catch {
    return NextResponse.json({
      data: [],
      meta: { source: "fallback" },
    });
  }
}
