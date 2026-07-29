import { randomBytes } from "node:crypto";

import { createPool } from "@vercel/postgres";

import {
  DEFAULT_RATING_OPTIONS,
  DEFAULT_REGION_OPTIONS,
  DEFAULT_SERVICE_TYPE_OPTIONS,
  type DirectoryOpportunity,
} from "./directory-constants.ts";
import { classifyDirectoryDatabaseError, type DirectoryDatabaseStatus } from "./directory-db-status.ts";
import {
  MAX_DIRECTORY_EXPORT_ROWS,
  type DirectoryExportRow,
  type DirectoryExportScope,
} from "./directory-export.ts";
import {
  getFallbackFilterOptions,
  getFallbackServiceTypeCounts,
  getFallbackProvider,
  getFallbackOpportunityStats,
  getFallbackStats,
  listFallbackProvidersForExport,
  searchFallbackProviders,
} from "./directory-fallback.ts";
import type { DirectorySearchParams } from "./directory-filters.ts";
import type { NormalizedLeadRequest } from "./directory-leads.ts";

export interface DirectoryProviderSummary {
  id: string;
  slug: string | null;
  name: string;
  type: string | null;
  town: string | null;
  county: string | null;
  postcode: string | null;
  region: string | null;
  phone: string | null;
  website: string | null;
  overall_rating: string | null;
  registration_date: string | null;
  service_types: string | null;
  specialisms: string | null;
  number_of_beds: number | null;
  last_inspection_date: string | null;
}

export interface DirectoryProviderDetail extends DirectoryProviderSummary {
  address_line1: string | null;
  address_line2: string | null;
  local_authority: string | null;
  rating_safe: string | null;
  rating_effective: string | null;
  rating_caring: string | null;
  rating_responsive: string | null;
  rating_well_led: string | null;
  inspection_report_url: string | null;
  meta_title: string | null;
  meta_description: string | null;
}

export interface DirectorySearchResult {
  providers: DirectoryProviderSummary[];
  total: number;
  totalPages: number;
}

export interface DirectoryFilterOptions {
  regions: string[];
  serviceTypes: string[];
  ratings: string[];
}

export interface DirectoryServiceTypeCount {
  service_type: string;
  provider_count: number;
}

export interface DirectoryStats {
  totalProviders: number;
  totalRegions: number;
}

export interface DirectoryOpportunityStats {
  totalProviders: number;
  newLast90Days: number;
  inadequate: number;
  requiresImprovement: number;
  notYetInspected: number;
  staleInspection: number;
}

interface SearchRow extends DirectoryProviderSummary {
  full_count: number;
  search_rank: number;
}

interface ProviderDetailRow extends DirectoryProviderDetail {}

interface TokenRow {
  token: string;
  region: string;
  service_type: string;
  rating: string;
}

function resolveConnectionString() {
  const raw = process.env.POSTGRES_URL || process.env.DATABASE_URL;
  return raw ? raw.replace(/^['"]|['"]$/g, "") : null;
}

let sqlPool: ReturnType<typeof createPool> | null = null;
let cachedConnectionString: string | null = null;

function getSql() {
  const connectionString = resolveConnectionString();
  if (!connectionString) {
    throw new Error("POSTGRES_URL or DATABASE_URL is not configured.");
  }

  if (!sqlPool || cachedConnectionString !== connectionString) {
    sqlPool = createPool({
      connectionString,
      max: 5,
      connectionTimeoutMillis: 5_000,
      idleTimeoutMillis: 10_000,
    });
    cachedConnectionString = connectionString;
  }

  return sqlPool;
}

function rethrowUnexpectedDatabaseError(error: unknown): void {
  if (classifyDirectoryDatabaseError(error) === "unknown") {
    throw error;
  }
}

function assertDatabaseConfigured() {
  if (!resolveConnectionString()) {
    throw new Error("POSTGRES_URL or DATABASE_URL is not configured.");
  }
}

export async function isDirectoryDatabaseAvailable(): Promise<boolean> {
  const status = await getDirectoryDatabaseStatus();
  return status.available;
}

export async function getDirectoryDatabaseStatus(): Promise<DirectoryDatabaseStatus> {
  try {
    assertDatabaseConfigured();
    await getSql().query("SELECT 1");
    return { available: true, reason: "ok" };
  } catch (error) {
    return {
      available: false,
      reason: classifyDirectoryDatabaseError(error),
    };
  }
}

function buildOpportunityClause(opportunity: DirectoryOpportunity | "") {
  switch (opportunity) {
    case "new_90":
      return "registration_date >= CURRENT_DATE - INTERVAL '90 days'";
    case "inadequate":
      return "overall_rating = 'Inadequate'";
    case "requires_improvement":
      return "overall_rating = 'Requires Improvement'";
    case "not_yet_inspected":
      return "overall_rating = 'Not Yet Inspected'";
    case "stale_inspection":
      return "(last_inspection_date IS NULL OR last_inspection_date < CURRENT_DATE - INTERVAL '3 years')";
    default:
      return "";
  }
}

function buildWhereClause(
  filters: Pick<DirectorySearchParams, "query" | "region" | "serviceType" | "rating" | "opportunity">,
) {
  const params: Array<string | number> = [];
  const clauses = ["status = 'ACTIVE'"];
  const searchVector =
    "to_tsvector('english', coalesce(name,'') || ' ' || coalesce(town,'') || ' ' || coalesce(county,'') || ' ' || coalesce(region,'') || ' ' || coalesce(service_types,'') || ' ' || coalesce(specialisms,''))";

  let tsQueryIndex: number | null = null;

  if (filters.query) {
    params.push(`%${filters.query}%`);
    const ilikeIndex = params.length;
    params.push(filters.query);
    tsQueryIndex = params.length;

    clauses.push(
      `(
        name ILIKE $${ilikeIndex}
        OR town ILIKE $${ilikeIndex}
        OR county ILIKE $${ilikeIndex}
        OR region ILIKE $${ilikeIndex}
        OR service_types ILIKE $${ilikeIndex}
        OR specialisms ILIKE $${ilikeIndex}
        OR ${searchVector} @@ websearch_to_tsquery('english', $${tsQueryIndex})
      )`,
    );
  }

  if (filters.region) {
    params.push(filters.region);
    clauses.push(`region = $${params.length}`);
  }

  if (filters.serviceType) {
    params.push(filters.serviceType);
    clauses.push(
      `EXISTS (
        SELECT 1
        FROM unnest(string_to_array(coalesce(service_types, ''), '|')) AS service_type
        WHERE btrim(service_type) = $${params.length}
      )`,
    );
  }

  if (filters.rating) {
    params.push(filters.rating);
    clauses.push(`overall_rating = $${params.length}`);
  }

  const opportunityClause = buildOpportunityClause(filters.opportunity);
  if (opportunityClause) {
    clauses.push(opportunityClause);
  }

  return { clauses, params, searchVector, tsQueryIndex };
}

function buildSearchSql(filters: DirectorySearchParams) {
  const { clauses, params, searchVector, tsQueryIndex } = buildWhereClause(filters);

  params.push(filters.perPage);
  const limitIndex = params.length;
  params.push(filters.offset);
  const offsetIndex = params.length;

  const orderBy = tsQueryIndex ? "search_rank DESC, name ASC" : "name ASC";
  const rankSelect = tsQueryIndex
    ? `ts_rank(${searchVector}, websearch_to_tsquery('english', $${tsQueryIndex})) AS search_rank`
    : "0::real AS search_rank";

  const query = `
    SELECT
      id,
      slug,
      name,
      type,
      town,
      county,
      postcode,
      region,
      phone,
      website,
      overall_rating,
      registration_date::text AS registration_date,
      service_types,
      specialisms,
      number_of_beds,
      last_inspection_date::text AS last_inspection_date,
      COUNT(*) OVER()::int AS full_count,
      ${rankSelect}
    FROM care_providers
    WHERE ${clauses.join(" AND ")}
    ORDER BY ${orderBy}
    LIMIT $${limitIndex}
    OFFSET $${offsetIndex}
  `;

  return { query, params };
}

function normalizeOptions(values: string[], fallbacks: string[]) {
  const cleaned = values.map((value) => value.trim()).filter(Boolean);
  return cleaned.length > 0 ? cleaned : fallbacks;
}

function sortRatings(ratings: string[]) {
  const order = new Map(DEFAULT_RATING_OPTIONS.map((rating, index) => [rating, index]));
  return [...ratings].sort((left, right) => {
    const leftIndex = order.get(left);
    const rightIndex = order.get(right);

    if (leftIndex !== undefined && rightIndex !== undefined) {
      return leftIndex - rightIndex;
    }

    if (leftIndex !== undefined) {
      return -1;
    }

    if (rightIndex !== undefined) {
      return 1;
    }

    return left.localeCompare(right);
  });
}

export async function getDirectoryFilterOptions(): Promise<DirectoryFilterOptions> {
  try {
    assertDatabaseConfigured();

    const [regionsRes, serviceTypesRes, ratingsRes] = await Promise.all([
      getSql().query<{ region: string }>(
        `
          SELECT DISTINCT region
          FROM care_providers
          WHERE status = 'ACTIVE' AND region IS NOT NULL AND region <> ''
          ORDER BY region
        `,
      ),
      getSql().query<{ service_type: string }>(
        `
          SELECT DISTINCT btrim(service_type) AS service_type
          FROM care_providers,
          unnest(string_to_array(coalesce(service_types, ''), '|')) AS service_type
          WHERE status = 'ACTIVE' AND btrim(service_type) <> ''
          ORDER BY service_type
        `,
      ),
      getSql().query<{ overall_rating: string }>(
        `
          SELECT DISTINCT overall_rating
          FROM care_providers
          WHERE status = 'ACTIVE' AND overall_rating IS NOT NULL AND overall_rating <> ''
        `,
      ),
    ]);

    return {
      regions: normalizeOptions(regionsRes.rows.map((row) => row.region), DEFAULT_REGION_OPTIONS),
      serviceTypes: normalizeOptions(
        serviceTypesRes.rows.map((row) => row.service_type),
        DEFAULT_SERVICE_TYPE_OPTIONS,
      ),
      ratings: sortRatings(
        normalizeOptions(ratingsRes.rows.map((row) => row.overall_rating), DEFAULT_RATING_OPTIONS),
      ),
    };
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    try {
      return await getFallbackFilterOptions();
    } catch {
      return {
        regions: DEFAULT_REGION_OPTIONS,
        serviceTypes: DEFAULT_SERVICE_TYPE_OPTIONS,
        ratings: DEFAULT_RATING_OPTIONS,
      };
    }
  }
}

export async function getDirectoryServiceTypeCounts(): Promise<DirectoryServiceTypeCount[]> {
  try {
    assertDatabaseConfigured();

    const result = await getSql().query<DirectoryServiceTypeCount>(
      `
        SELECT btrim(service_type) AS service_type, COUNT(*)::int AS provider_count
        FROM care_providers,
        unnest(string_to_array(coalesce(service_types, ''), '|')) AS service_type
        WHERE status = 'ACTIVE' AND btrim(service_type) <> ''
        GROUP BY btrim(service_type)
        ORDER BY service_type
      `,
    );

    return result.rows;
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return getFallbackServiceTypeCounts();
  }
}

export async function getDirectoryStats(): Promise<DirectoryStats> {
  try {
    assertDatabaseConfigured();

    const result = await getSql().query<{ total_providers: number; total_regions: number }>(
      `
        SELECT
          COUNT(*)::int AS total_providers,
          COUNT(DISTINCT region)::int AS total_regions
        FROM care_providers
        WHERE status = 'ACTIVE'
      `,
    );

    return {
      totalProviders: result.rows[0]?.total_providers ?? 0,
      totalRegions: result.rows[0]?.total_regions ?? 0,
    };
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return getFallbackStats();
  }
}

export async function getDirectoryOpportunityStats(): Promise<DirectoryOpportunityStats> {
  try {
    assertDatabaseConfigured();

    const result = await getSql().query<{
      total_providers: number;
      new_last_90_days: number;
      inadequate: number;
      requires_improvement: number;
      not_yet_inspected: number;
      stale_inspection: number;
    }>(
      `
        SELECT
          COUNT(*)::int AS total_providers,
          COUNT(*) FILTER (WHERE registration_date >= CURRENT_DATE - INTERVAL '90 days')::int AS new_last_90_days,
          COUNT(*) FILTER (WHERE overall_rating = 'Inadequate')::int AS inadequate,
          COUNT(*) FILTER (WHERE overall_rating = 'Requires Improvement')::int AS requires_improvement,
          COUNT(*) FILTER (WHERE overall_rating = 'Not Yet Inspected')::int AS not_yet_inspected,
          COUNT(*) FILTER (
            WHERE last_inspection_date IS NULL OR last_inspection_date < CURRENT_DATE - INTERVAL '3 years'
          )::int AS stale_inspection
        FROM care_providers
        WHERE status = 'ACTIVE'
      `,
    );

    const row = result.rows[0];
    return {
      totalProviders: row?.total_providers ?? 0,
      newLast90Days: row?.new_last_90_days ?? 0,
      inadequate: row?.inadequate ?? 0,
      requiresImprovement: row?.requires_improvement ?? 0,
      notYetInspected: row?.not_yet_inspected ?? 0,
      staleInspection: row?.stale_inspection ?? 0,
    };
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return getFallbackOpportunityStats();
  }
}

export async function searchDirectoryProviders(filters: DirectorySearchParams): Promise<DirectorySearchResult> {
  try {
    assertDatabaseConfigured();

    const { query, params } = buildSearchSql(filters);
    const result = await getSql().query<SearchRow>(query, params);
    const total = result.rows[0]?.full_count ?? 0;

    return {
      providers: result.rows.map(({ full_count: _fullCount, search_rank: _searchRank, ...provider }) => provider),
      total,
      totalPages: total === 0 ? 0 : Math.ceil(total / filters.perPage),
    };
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return searchFallbackProviders(filters);
  }
}

export async function getDirectoryProvider(slugOrId: string): Promise<DirectoryProviderDetail | null> {
  try {
    assertDatabaseConfigured();

    const result = await getSql().query<ProviderDetailRow>(
      `
        SELECT
          id,
          slug,
          name,
          type,
          address_line1,
          address_line2,
          town,
          county,
          postcode,
          region,
          local_authority,
          phone,
          website,
          overall_rating,
          registration_date::text AS registration_date,
          rating_safe,
          rating_effective,
          rating_caring,
          rating_responsive,
          rating_well_led,
          service_types,
          specialisms,
          number_of_beds,
          last_inspection_date::text AS last_inspection_date,
          inspection_report_url,
          meta_title,
          meta_description
        FROM care_providers
        WHERE status = 'ACTIVE' AND (slug = $1 OR id = $1)
        LIMIT 1
      `,
      [slugOrId],
    );

    return result.rows[0] ?? null;
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return getFallbackProvider(slugOrId);
  }
}

export async function createLeadAndToken(input: NormalizedLeadRequest): Promise<{ token: string }> {
  if (input.opportunity) {
    throw new Error("Database lead tokens do not support opportunity-specific scopes yet.");
  }

  assertDatabaseConfigured();

  const client = await getSql().connect();
  const token = randomBytes(24).toString("base64url");

  try {
    await client.query("BEGIN");
    const leadResult = await client.query<{ id: number }>(
      `
        INSERT INTO leads (email, region, service_type, rating)
        VALUES ($1, $2, $3, $4)
        RETURNING id
      `,
      [input.email, input.region, input.serviceType, input.rating],
    );

    await client.query(
      `
        INSERT INTO export_access_tokens (token, lead_id, region, service_type, rating)
        VALUES ($1, $2, $3, $4, $5)
      `,
      [token, leadResult.rows[0].id, input.region, input.serviceType, input.rating],
    );

    await client.query("COMMIT");
    return { token };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

export async function getExportScopeForToken(token: string): Promise<DirectoryExportScope | null> {
  assertDatabaseConfigured();

  const result = await getSql().query<TokenRow>(
    `
      SELECT token, region, service_type, rating
      FROM export_access_tokens
      WHERE token = $1
        AND expires_at > NOW()
      LIMIT 1
    `,
    [token],
  );

  if (!result.rows[0]) {
    return null;
  }

  return {
    region: result.rows[0].region ?? "",
    serviceType: result.rows[0].service_type ?? "",
    rating: result.rows[0].rating ?? "",
  };
}

export async function listProvidersForExport(scope: DirectoryExportScope): Promise<DirectoryExportRow[]> {
  try {
    assertDatabaseConfigured();

    const { clauses, params } = buildWhereClause({
      query: "",
      region: scope.region,
      serviceType: scope.serviceType,
      rating: scope.rating,
      opportunity: scope.opportunity ?? "",
    });
    params.push(MAX_DIRECTORY_EXPORT_ROWS + 1);
    const limitIndex = params.length;
    const result = await getSql().query<DirectoryExportRow>(
      `
        SELECT
          name,
          slug,
          region,
          service_types,
          specialisms,
          phone,
          website,
          overall_rating,
          registration_date::text AS registration_date,
          inspection_report_url
        FROM care_providers
        WHERE ${clauses.join(" AND ")}
        ORDER BY name ASC
        LIMIT $${limitIndex}
      `,
      params,
    );
    return result.rows;
  } catch (error) {
    rethrowUnexpectedDatabaseError(error);
    return listFallbackProvidersForExport(scope);
  }
}
