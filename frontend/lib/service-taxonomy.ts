import registry from "../data/service-taxonomy.json" with { type: "json" };

export type CanonicalService = {
  slug: string;
  name: string;
  category: string;
  aliases: string[];
};

const services = registry as CanonicalService[];
const bySlug = new Map(services.map((entry) => [entry.slug, entry]));
const byAlias = new Map(
  services.flatMap((entry) => entry.aliases.map((alias) => [alias.trim().toLocaleLowerCase("en-GB"), entry] as const)),
);

export function canonicalServices(): CanonicalService[] {
  return services;
}

export function resolveServiceAliases(value: string): string[] {
  const cleaned = value.trim();
  const entry = bySlug.get(cleaned) ?? byAlias.get(cleaned.toLocaleLowerCase("en-GB"));
  return entry?.aliases ?? (cleaned ? [cleaned] : []);
}

export function canonicalizeServiceCounts(rows: Array<{ service_type: string; provider_count: number }>) {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const entry = byAlias.get(row.service_type.trim().toLocaleLowerCase("en-GB"));
    if (!entry) continue;
    counts.set(entry.slug, (counts.get(entry.slug) ?? 0) + Number(row.provider_count || 0));
  }
  return services
    .filter((entry) => (counts.get(entry.slug) ?? 0) > 0)
    .map((entry) => ({
      service_type: entry.slug,
      service_name: entry.name,
      category: entry.category,
      provider_count: counts.get(entry.slug) ?? 0,
      source_aliases: entry.aliases,
    }));
}
