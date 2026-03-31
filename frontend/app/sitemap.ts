import type { MetadataRoute } from "next";

const BASE = "https://caregist.co.uk";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date().toISOString();

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE}/search`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${BASE}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE}/compare`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${BASE}/api`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/find-care`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
  ];

  // Region pages (9 known regions)
  const regions = [
    "south-east", "london", "north-west", "east", "west-midlands",
    "south-west", "yorkshire-humberside", "east-midlands", "north-east",
  ];
  const regionPages: MetadataRoute.Sitemap = regions.map((r) => ({
    url: `${BASE}/region/${r}`,
    lastModified: now,
    changeFrequency: "weekly" as const,
    priority: 0.7,
  }));

  // Fetch top cities and LAs for dynamic pages
  let cityPages: MetadataRoute.Sitemap = [];
  let laPages: MetadataRoute.Sitemap = [];

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const citiesRes = await fetch(`${apiBase}/api/v1/cities`, { next: { revalidate: 86400 } });
    if (citiesRes.ok) {
      const cities = await citiesRes.json();
      const topCities = (cities.data || []).slice(0, 200);
      for (const city of topCities) {
        for (const rating of ["outstanding", "good", "care"]) {
          cityPages.push({
            url: `${BASE}/${rating}-care-homes/${city.slug}`,
            lastModified: now,
            changeFrequency: "weekly",
            priority: 0.6,
          });
        }
      }
    }
  } catch {
    // Cities unavailable — sitemap still works with static pages
  }

  try {
    const laRes = await fetch(`${apiBase}/api/v1/regions/local-authorities`, { next: { revalidate: 86400 } });
    if (laRes.ok) {
      const las = await laRes.json();
      laPages = (las.data || []).slice(0, 150).map((la: any) => ({
        url: `${BASE}/region/${la.slug}`,
        lastModified: now,
        changeFrequency: "weekly" as const,
        priority: 0.6,
      }));
    }
  } catch {
    // LAs unavailable
  }

  return [...staticPages, ...regionPages, ...laPages, ...cityPages];
}
