import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      error: "Filtered lead-list exports are no longer offered. Use CareGist Radar for verified change events.",
    },
    { status: 410 },
  );
}
