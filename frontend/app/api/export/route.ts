import { NextRequest, NextResponse } from "next/server";

import { readDirectoryAccessToken } from "@/lib/directory-access-token";
import { isDirectoryOpportunity } from "@/lib/directory-constants";
import { getExportScopeForToken, listProvidersForExport } from "@/lib/directory-db";
import {
  MAX_DIRECTORY_EXPORT_ROWS,
  providersToCsv,
  resolveExportScope,
  type DirectoryExportScope,
} from "@/lib/directory-export";

export const runtime = "nodejs";

function buildFilename(scope: { region: string; serviceType: string; rating: string; opportunity?: string }) {
  const parts = ["caregist"];
  if (scope.opportunity) parts.push(scope.opportunity);
  if (scope.region) parts.push(scope.region);
  if (scope.serviceType) parts.push(scope.serviceType);
  if (scope.rating) parts.push(scope.rating);

  return `${parts.join("-").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "caregist-export"}.csv`;
}

export async function GET(request: NextRequest) {
  if (process.env.DIRECTORY_EXPORT_DELIVERY_ENABLED !== "true") {
    return NextResponse.json(
      { error: "Export delivery is awaiting Human Gate approval." },
      { status: 503, headers: { "Cache-Control": "private, no-store" } },
    );
  }

  const token = request.nextUrl.searchParams.get("token")?.trim();

  if (!token) {
    return NextResponse.json({ error: "Export token required." }, { status: 401 });
  }

  const opportunity = request.nextUrl.searchParams.get("opportunity")?.trim() ?? "";
  let storedScope = readDirectoryAccessToken(token);
  if (!storedScope) {
    try {
      storedScope = await getExportScopeForToken(token);
    } catch {
      return NextResponse.json({ error: "Export service is temporarily unavailable." }, { status: 503 });
    }
  }
  if (!storedScope) {
    return NextResponse.json({ error: "Export token is invalid or expired." }, { status: 401 });
  }

  try {
    const scope = resolveExportScope(storedScope, {
      region: request.nextUrl.searchParams.get("region")?.trim() ?? "",
      serviceType: request.nextUrl.searchParams.get("service_type")?.trim() ?? "",
      rating: request.nextUrl.searchParams.get("rating")?.trim() ?? "",
      opportunity: isDirectoryOpportunity(opportunity) ? opportunity : "",
    });
    // Preserve the inferred type outside the validation block.
    return await createExportResponse(scope);
  } catch {
    return NextResponse.json({ error: "Export token does not allow that segment." }, { status: 403 });
  }
}

async function createExportResponse(scope: DirectoryExportScope) {
  try {
    const rows = await listProvidersForExport(scope);
    if (rows.length > MAX_DIRECTORY_EXPORT_ROWS) {
      return NextResponse.json(
        { error: `This export exceeds ${MAX_DIRECTORY_EXPORT_ROWS.toLocaleString("en-GB")} rows. Add filters and try again.` },
        { status: 413 },
      );
    }
    const csv = providersToCsv(rows);

    return new NextResponse(csv, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${buildFilename(scope)}"`,
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "Export service is temporarily unavailable." }, { status: 503 });
  }
}
