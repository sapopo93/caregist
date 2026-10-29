/** Brief coverage uses the sealed edition's Python-produced rating contract.
 * Missing contracts fail closed, rather than falling back to directory ratings.
 */
export function territoryRatingCoverageSql(opportunity: string): string {
  const predicates: Record<string, string> = {
    inadequate: "r->>'status' = 'current' AND r->>'value' = 'Inadequate'",
    requires_improvement: "r->>'status' = 'current' AND r->>'value' = 'Requires improvement'",
    not_yet_inspected: "r->>'status' = 'unrated'",
  };
  const predicate = predicates[opportunity];
  if (!predicate) throw new Error("Unsupported rating scope");
  return `WITH edition AS (
    SELECT id, location_count, source_retrieved_at FROM territory_brief_source_editions
    ORDER BY source_retrieved_at DESC, id DESC LIMIT 1
  ), members AS (
    SELECT s.*, payload->'rating_resolution' AS r
    FROM territory_brief_source_locations s JOIN edition e ON s.edition_id = e.id
  ), valid AS (
    SELECT e.id FROM edition e
    WHERE e.source_retrieved_at BETWEEN now() - interval '8 days' AND now()
      AND (SELECT count(*) FROM members) = e.location_count
      AND NOT EXISTS (SELECT 1 FROM members
        WHERE r->>'contract_version' IS DISTINCT FROM '2')
  )
  SELECT count(DISTINCT (payload->>'providerId'))::int AS provider_count,
    max(r->>'publication_date') AS most_recent_inspection,
    max(payload->>'registrationDate') AS most_recent_registration,
    (SELECT id::text FROM valid) AS source_edition_id
  FROM members WHERE edition_id = (SELECT id FROM valid)
    AND lower(btrim(payload->>'registrationStatus')) = 'registered'
    AND upper(btrim(coalesce(payload->>'dormancy', ''))) NOT LIKE 'Y%'
    AND lower(region) = lower($1)
    AND (cardinality($2::text[]) = 0 OR EXISTS (SELECT 1 FROM jsonb_array_elements(
      coalesce(payload->'gacServiceTypes', '[]'::jsonb)) t WHERE lower(btrim(t->>'description')) = ANY(
      SELECT lower(alias) FROM unnest($2::text[]) alias)))
    AND (${predicate})`;
}
