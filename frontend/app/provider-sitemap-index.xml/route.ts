import { NextResponse } from "next/server";

import { getPublicApiBase } from "@/lib/server-api-config";

const BASE = "https://caregist.co.uk";
const PAGE_SIZE = 50000;

export async function GET() {
  const apiBase = getPublicApiBase();
  const res = await fetch(`${apiBase}/api/v1/sitemaps/providers/count`, {
    next: { revalidate: 86400 },
  });

  if (!res.ok) {
    return new NextResponse("Provider sitemap index unavailable", { status: 503 });
  }

  const payload = await res.json();
  const total = Number(payload.total || 0);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const now = new Date().toISOString();

  const entries = Array.from({ length: pages }, (_, index) => `
    <sitemap>
      <loc>${BASE}/provider-sitemaps/${index}</loc>
      <lastmod>${now}</lastmod>
    </sitemap>`).join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${entries}
</sitemapindex>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "s-maxage=86400, stale-while-revalidate=86400",
    },
  });
}
