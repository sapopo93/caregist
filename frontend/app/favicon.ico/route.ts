import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

export function GET(request: NextRequest) {
  return NextResponse.redirect(new URL("/favicon.svg", request.url), 308);
}
