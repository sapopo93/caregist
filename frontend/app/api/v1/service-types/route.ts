import { NextResponse } from "next/server";

const FALLBACK_SERVICE_TYPES = [
  "Homecare Agencies",
  "Residential Homes",
  "Nursing Homes",
  "Doctors/Gps",
  "Dentist",
  "Supported Living",
];

function fallbackResponse() {
  return NextResponse.json({
    data: FALLBACK_SERVICE_TYPES.map((service_type) => ({ service_type, provider_count: 0 })),
    meta: { fallback: true },
  });
}

export async function GET() {
  const apiBase = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL;

  if (!apiBase) {
    return fallbackResponse();
  }

  try {
    const upstream = new URL("/api/v1/service-types", apiBase);
    const res = await fetch(upstream.toString(), { next: { revalidate: 3600 } });

    if (!res.ok) {
      return fallbackResponse();
    }

    const payload = await res.json();
    if (!payload || !Array.isArray(payload.data)) {
      return fallbackResponse();
    }

    return NextResponse.json(payload);
  } catch {
    return fallbackResponse();
  }
}
