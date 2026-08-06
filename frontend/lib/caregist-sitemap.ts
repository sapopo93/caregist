import type { MetadataRoute } from "next";

import { getSiteUrl } from "./site.ts";

const STATIC_SITEMAP_PATHS: Array<{
  path: string;
  changeFrequency: NonNullable<MetadataRoute.Sitemap[number]["changeFrequency"]>;
  priority: number;
}> = [
  { path: "", changeFrequency: "weekly", priority: 1 },
  { path: "/search", changeFrequency: "weekly", priority: 0.9 },
  { path: "/lead-list", changeFrequency: "weekly", priority: 0.8 },
  { path: "/privacy", changeFrequency: "monthly", priority: 0.3 },
  { path: "/terms", changeFrequency: "monthly", priority: 0.3 },
];

export function buildCareGistSitemap(baseUrl = getSiteUrl()): MetadataRoute.Sitemap {
  return STATIC_SITEMAP_PATHS.map(({ path, changeFrequency, priority }) => ({
    url: `${baseUrl}${path}`,
    changeFrequency,
    priority,
  }));
}

export function buildCareGistRobots(baseUrl = getSiteUrl()): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: [`${baseUrl}/sitemap.xml`, `${baseUrl}/provider-sitemap-index.xml`],
  };
}
