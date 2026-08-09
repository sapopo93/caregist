import type { MetadataRoute } from "next";

import { buildCareGistSitemap } from "@/lib/caregist-sitemap";

export default function sitemap(): MetadataRoute.Sitemap {
  return buildCareGistSitemap();
}
