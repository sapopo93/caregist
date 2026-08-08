/**
 * frontend/app/api/proxy/[...path]/route.ts
 *
 * Server-side proxy that injects the backend API_KEY before forwarding requests.
 * This is the ONLY place in the frontend that should call the backend directly.
 * Client-side code must call /api/proxy/... instead of the backend URL directly,
 * so that API_KEY (a server-only env var) is never exposed to the browser bundle.
 *
 * Related: F#4 — NEXT_PUBLIC_API_KEY removal.
 */
import { NextRequest, NextResponse } from "next/server";
import { getServerApiBase, getServerApiKey } from "@/lib/server-api-config";

export const runtime = "nodejs";

async function handler(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const apiBase = getServerApiBase();
  const apiKey = getServerApiKey();

  const upstreamPath = "/" + params.path.join("/");
  const upstreamUrl = new URL(upstreamPath, apiBase);

  // Forward query string
  request.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });

  const headers = new Headers();
  // Pass through content-type and accept headers
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("accept", accept);

  // Forward session cookies for authenticated requests (Spool auth integration)
  headers.set("cookie", request.headers.get("cookie") ?? "");

  // Inject API_KEY server-side — this env var is never sent to the browser
  headers.set("x-api-key", apiKey);

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.arrayBuffer()
      : undefined;

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl.toString(), {
      method: request.method,
      headers,
      body,
    });
  } catch (err) {
    console.error("[proxy] upstream fetch failed", err);
    return NextResponse.json({ error: "upstream_unavailable" }, { status: 502 });
  }

  const responseHeaders = new Headers();
  // Forward safe response headers
  const forwardHeaders = ["content-type", "cache-control", "etag", "last-modified"];
  for (const h of forwardHeaders) {
    const v = upstreamResponse.headers.get(h);
    if (v) responseHeaders.set(h, v);
  }

  return new NextResponse(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers: responseHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
