import "server-only";

import { access, readFile } from "node:fs/promises";
import { join } from "node:path";

export interface DirectoryFileProvider {
  id: string;
  slug: string | null;
  name: string;
  type: string | null;
  status: string;
  town: string | null;
  county: string | null;
  postcode: string | null;
  region: string | null;
  local_authority: string | null;
  phone: string | null;
  website: string | null;
  overall_rating: string | null;
  registration_date: string | null;
  rating_safe: string | null;
  rating_effective: string | null;
  rating_caring: string | null;
  rating_responsive: string | null;
  rating_well_led: string | null;
  service_types: string | null;
  specialisms: string | null;
  number_of_beds: number | null;
  last_inspection_date: string | null;
  inspection_report_url: string | null;
  address_line1: string | null;
  address_line2: string | null;
  meta_title: string | null;
  meta_description: string | null;
}

const SELECTED_COLUMNS = [
  "id",
  "slug",
  "name",
  "type",
  "status",
  "town",
  "county",
  "postcode",
  "region",
  "local_authority",
  "phone",
  "website",
  "overall_rating",
  "registration_date",
  "rating_safe",
  "rating_effective",
  "rating_caring",
  "rating_responsive",
  "rating_well_led",
  "service_types",
  "specialisms",
  "number_of_beds",
  "last_inspection_date",
  "inspection_report_url",
  "address_line1",
  "address_line2",
  "meta_title",
  "meta_description",
] as const;

// Keep filesystem calls on primitive paths. Turbopack can evaluate module URL
// objects in a different VM realm, which Node rejects even before readFile runs.
// The frontend service root is the working directory locally and on Vercel.
const FALLBACK_DATASET_PATH = join(process.cwd(), "data", "directory-fallback-full.csv");

let providersPromise: Promise<DirectoryFileProvider[]> | null = null;
let datasetPathPromise: Promise<string> | null = null;

function parseCsvLine(line: string): string[] {
  const values: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];

    if (inQuotes) {
      if (character === '"') {
        if (line[index + 1] === '"') {
          current += '"';
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        current += character;
      }
      continue;
    }

    if (character === '"') {
      inQuotes = true;
      continue;
    }

    if (character === ",") {
      values.push(current);
      current = "";
      continue;
    }

    current += character;
  }

  values.push(current);
  return values;
}

function asNullableString(value: string | undefined): string | null {
  const trimmed = String(value ?? "").trim();
  return trimmed ? trimmed : null;
}

function asNullableNumber(value: string | undefined): number | null {
  const trimmed = String(value ?? "").trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

async function resolveDatasetPath(): Promise<string> {
  if (!datasetPathPromise) {
    datasetPathPromise = (async () => {
      await access(FALLBACK_DATASET_PATH);
      return FALLBACK_DATASET_PATH;
    })();
  }

  return datasetPathPromise;
}

async function loadProvidersFromCsv(): Promise<DirectoryFileProvider[]> {
  const datasetPath = await resolveDatasetPath();
  const content = await readFile(datasetPath, "utf8");
  const lines = content.split(/\r?\n/).filter(Boolean);

  if (lines.length === 0) {
    return [];
  }

  const header = parseCsvLine(lines[0]);
  const columnIndexes = new Map<string, number>();
  header.forEach((column, index) => {
    columnIndexes.set(column, index);
  });

  const selectedIndexes = SELECTED_COLUMNS.map((column) => [column, columnIndexes.get(column) ?? -1] as const);
  const providers: DirectoryFileProvider[] = [];

  for (const line of lines.slice(1)) {
    const values = parseCsvLine(line);
    const row = new Map<string, string>();

    for (const [column, index] of selectedIndexes) {
      row.set(column, index >= 0 ? values[index] ?? "" : "");
    }

    providers.push({
      id: row.get("id") ?? "",
      slug: asNullableString(row.get("slug")),
      name: row.get("name") ?? "",
      type: asNullableString(row.get("type")),
      status: row.get("status") ?? "",
      town: asNullableString(row.get("town")),
      county: asNullableString(row.get("county")),
      postcode: asNullableString(row.get("postcode")),
      region: asNullableString(row.get("region")),
      local_authority: asNullableString(row.get("local_authority")),
      phone: asNullableString(row.get("phone")),
      website: asNullableString(row.get("website")),
      overall_rating: asNullableString(row.get("overall_rating")),
      registration_date: asNullableString(row.get("registration_date")),
      rating_safe: asNullableString(row.get("rating_safe")),
      rating_effective: asNullableString(row.get("rating_effective")),
      rating_caring: asNullableString(row.get("rating_caring")),
      rating_responsive: asNullableString(row.get("rating_responsive")),
      rating_well_led: asNullableString(row.get("rating_well_led")),
      service_types: asNullableString(row.get("service_types")),
      specialisms: asNullableString(row.get("specialisms")),
      number_of_beds: asNullableNumber(row.get("number_of_beds")),
      last_inspection_date: asNullableString(row.get("last_inspection_date")),
      inspection_report_url: asNullableString(row.get("inspection_report_url")),
      address_line1: asNullableString(row.get("address_line1")),
      address_line2: asNullableString(row.get("address_line2")),
      meta_title: asNullableString(row.get("meta_title")),
      meta_description: asNullableString(row.get("meta_description")),
    });
  }

  return providers;
}

export async function loadDirectoryFileProviders(): Promise<DirectoryFileProvider[]> {
  if (!providersPromise) {
    providersPromise = loadProvidersFromCsv().catch((error) => {
      providersPromise = null;
      throw error;
    });
  }

  return providersPromise;
}

export async function hasDirectoryFallbackDataset(): Promise<boolean> {
  try {
    await resolveDatasetPath();
    return true;
  } catch {
    return false;
  }
}
