import type { DirectoryOpportunity } from "./directory-constants.ts";

export interface DirectoryExportScope {
  region: string;
  serviceType: string;
  rating: string;
  opportunity?: DirectoryOpportunity | "";
}

export interface DirectoryExportRow {
  name: string | null;
  slug: string | null;
  region: string | null;
  service_types: string | null;
  specialisms: string | null;
  phone: string | null;
  website: string | null;
  overall_rating: string | null;
  registration_date: string | null;
  inspection_report_url: string | null;
}

export const MAX_DIRECTORY_EXPORT_ROWS = 10_000;
export const CQC_SOURCE_ATTRIBUTION =
  "Care Quality Commission data, licensed under the Open Government Licence v3.0";

const CSV_COLUMNS: Array<keyof DirectoryExportRow> = [
  "name",
  "slug",
  "region",
  "service_types",
  "specialisms",
  "phone",
  "website",
  "overall_rating",
  "registration_date",
  "inspection_report_url",
];

function escapeCsvCell(value: string | null): string {
  const raw = String(value ?? "");
  const text = /^[\t\r ]*[=+\-@]/.test(raw) ? `'${raw}` : raw;
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function resolveExportScope(
  storedScope: DirectoryExportScope,
  requestedScope: DirectoryExportScope,
): DirectoryExportScope {
  const resolved: DirectoryExportScope = {
    region: requestedScope.region || storedScope.region,
    serviceType: requestedScope.serviceType || storedScope.serviceType,
    rating: requestedScope.rating || storedScope.rating,
    opportunity: requestedScope.opportunity || storedScope.opportunity || "",
  };

  if (
    resolved.region !== storedScope.region ||
    resolved.serviceType !== storedScope.serviceType ||
    resolved.rating !== storedScope.rating ||
    (resolved.opportunity ?? "") !== (storedScope.opportunity ?? "")
  ) {
    throw new Error("Requested export scope does not match the issued access token.");
  }

  return resolved;
}

export function providersToCsv(rows: DirectoryExportRow[]): string {
  const header = [...CSV_COLUMNS, "source_attribution"].join(",");
  const lines = rows.map((row) =>
    [
      ...CSV_COLUMNS.map((column) => escapeCsvCell(row[column] ?? null)),
      escapeCsvCell(CQC_SOURCE_ATTRIBUTION),
    ].join(","),
  );

  return [header, ...lines].join("\n");
}
