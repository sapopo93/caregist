import { NextResponse } from "next/server";

import { getPublicApiBase } from "@/lib/server-api-config";

const BASE = "https://caregist.co.uk";
const PAGE_SIZE = 50000;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const page = Number(id);
  if (!Number.isFinite(page) || page < 0) {
    return new NextResponse("Invalid sitemap page", { status: 400 });
  }

  const apiBase = getPublicApiBase();
  const res = await fetch(`${apiBase}/api/v1/sitemaps/providers?offset=${page * PAGE_SIZE}&limit=${PAGE_SIZE}`, {
    next: { revalidate: 86400 },
  });

  if (!res.ok) {
    return new NextResponse("Provider sitemap unavailable", { status: 503 });
  }

  const payload = await res.json();
  const urls = (payload.data || [])
    .map((row: { slug: string; updated_at?: string | null }) => `
      <url>
        <loc>${BASE}/provider/${row.slug}</loc>
        ${row.updated_at ? `<lastmod>${row.updated_at}</lastmod>` : ""}
        <changefreq>daily</changefreq>
        <priority>0.6</priority>
      </url>`)
    .join("");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${urls}
</urlset>`;

  return new NextResponse(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "s-maxage=86400, stale-while-revalidate=86400",
    },
  });
}
