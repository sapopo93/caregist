import { NextResponse } from "next/server";

import { getServerApiBase } from "@/lib/server-api-config";
import { getSiteUrl } from "@/lib/site";

const PAGE_SIZE = 5000;

export async function GET() {
  const base = getSiteUrl();
  let res: Response;
  try {
    const apiBase = getServerApiBase();
    res = await fetch(`${apiBase}/api/v1/sitemaps/providers/count`, {
      next: { revalidate: 86400 },
    });
  } catch {
    return new NextResponse("Provider sitemap index unavailable", { status: 503 });
  }

  if (!res.ok) {
    return new NextResponse("Provider sitemap index unavailable", { status: 503 });
  }

  const payload = await res.json();
  const total = Number(payload.total || 0);
  if (!Number.isSafeInteger(total) || total <= 0) {
    return new NextResponse("Provider sitemap index unavailable", { status: 503 });
  }
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const now = new Date().toISOString();

  const entries = Array.from({ length: pages }, (_, index) => `
    <sitemap>
      <loc>${base}/provider-sitemaps/${index}</loc>
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
