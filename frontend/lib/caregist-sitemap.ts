import type { MetadataRoute } from "next";

import { getSiteUrl } from "./site.ts";

const STATIC_SITEMAP_PATHS: Array<{
  path: string;
  changeFrequency: NonNullable<MetadataRoute.Sitemap[number]["changeFrequency"]>;
  priority: number;
}> = [
  { path: "", changeFrequency: "weekly", priority: 1 },
  { path: "/search", changeFrequency: "weekly", priority: 0.9 },
  { path: "/pricing", changeFrequency: "weekly", priority: 0.8 },
  { path: "/pricing/territory", changeFrequency: "weekly", priority: 0.8 },
  { path: "/territory-opportunity-brief", changeFrequency: "monthly", priority: 0.7 },
  { path: "/intelligence-feed", changeFrequency: "monthly", priority: 0.7 },
  { path: "/why-caregist", changeFrequency: "monthly", priority: 0.6 },
  { path: "/data-status", changeFrequency: "daily", priority: 0.5 },
  { path: "/find-care", changeFrequency: "monthly", priority: 0.5 },
  { path: "/acceptable-use", changeFrequency: "monthly", priority: 0.3 },
  { path: "/cookies", changeFrequency: "monthly", priority: 0.3 },
  { path: "/privacy", changeFrequency: "monthly", priority: 0.3 },
  { path: "/terms", changeFrequency: "monthly", priority: 0.3 },
];

const ROBOTS_DISALLOW = [
  "/api/",
  "/admin",
  "/crm",
  "/dashboard",
  "/provider-dashboard/",
  "/login",
  "/signup",
  "/forgot-password",
  "/verify-email",
] as const;

export function buildCareGistSitemap(baseUrl = getSiteUrl()): MetadataRoute.Sitemap {
  return STATIC_SITEMAP_PATHS.map(({ path, changeFrequency, priority }) => ({
    url: `${baseUrl}${path}`,
    changeFrequency,
    priority,
  }));
}

export function buildCareGistRobots(baseUrl = getSiteUrl()): MetadataRoute.Robots {
  return {
    // Account, admin and API paths stay out of crawls. These rules used to live
    // in public/robots.txt, which this route silently shadowed.
    rules: { userAgent: "*", allow: "/", disallow: [...ROBOTS_DISALLOW] },
    sitemap: [`${baseUrl}/sitemap.xml`, `${baseUrl}/provider-sitemap-index.xml`],
  };
}
