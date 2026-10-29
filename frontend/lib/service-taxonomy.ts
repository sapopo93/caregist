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

/** Display name for a service slug; unknown values (legacy aliases) pass through. */
export function serviceTypeLabel(value: string): string {
  return bySlug.get(value.trim())?.name ?? value;
}

export function resolveServiceAliases(value: string): string[] {
  const cleaned = value.trim();
  const entry = bySlug.get(cleaned) ?? byAlias.get(cleaned.toLocaleLowerCase("en-GB"));
  return entry?.aliases ?? (cleaned ? [cleaned] : []);
}

/**
 * Canonical slugs that have at least one live source label. The search dropdown
 * is built from this so an option never offers a filter that returns nothing.
 */
export function canonicalSlugsWithLiveRows(liveLabels: string[]): string[] {
  const live = new Set(liveLabels.map((label) => label.trim().toLocaleLowerCase("en-GB")));
  return services
    .filter((entry) => entry.aliases.some((alias) => live.has(alias.trim().toLocaleLowerCase("en-GB"))))
    .map((entry) => entry.slug);
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
