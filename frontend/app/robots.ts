import type { MetadataRoute } from "next";

import { buildCareGistRobots } from "@/lib/caregist-sitemap";

export default function robots(): MetadataRoute.Robots {
  return buildCareGistRobots();
}
