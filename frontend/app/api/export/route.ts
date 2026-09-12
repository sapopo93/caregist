import { NextRequest, NextResponse } from "next/server";
import { getDownloadUrl, issueSignedToken, presignUrl } from "@vercel/blob";

import { readDirectoryAccessToken } from "@/lib/directory-access-token";
import { isDirectoryOpportunity } from "@/lib/directory-constants";
import {
  consumePaidDatasetDownload,
  consumePaidTerritoryBriefDownload,
  getExportScopeForToken,
  listProvidersForExport,
} from "@/lib/directory-db";
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
  const segmentedDeliveryEnabled = process.env.DIRECTORY_EXPORT_DELIVERY_ENABLED === "true";
  const fullDatasetDeliveryEnabled = process.env.FULL_DATASET_CHECKOUT_ENABLED === "true";
  const territoryDeliveryEnabled = process.env.TERRITORY_SELF_SERVE_CHECKOUT_ENABLED === "true";
  if (!segmentedDeliveryEnabled && !fullDatasetDeliveryEnabled && !territoryDeliveryEnabled) {
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
    if (!fullDatasetDeliveryEnabled && !territoryDeliveryEnabled) {
      return NextResponse.json({ error: "Export token is invalid or expired." }, { status: 401 });
    }
    try {
      storedScope = fullDatasetDeliveryEnabled ? await getExportScopeForToken(token) : null;
    } catch {
      return NextResponse.json({ error: "Export service is temporarily unavailable." }, { status: 503 });
    }
  }

  if (storedScope && !segmentedDeliveryEnabled) {
    return NextResponse.json(
      { error: "Segmented export delivery is awaiting Human Gate approval." },
      { status: 503, headers: { "Cache-Control": "private, no-store" } },
    );
  }
  if (!storedScope) {
    try {
      const paidDownload =
        (territoryDeliveryEnabled ? await consumePaidTerritoryBriefDownload(token) : null) ??
        (fullDatasetDeliveryEnabled ? await consumePaidDatasetDownload(token) : null);
      if (!paidDownload) {
        return NextResponse.json({ error: "Export token is invalid, expired, refunded, or exhausted." }, { status: 401 });
      }
      const signedToken = await issueSignedToken({ operations: ["get"] });
      const { presignedUrl } = await presignUrl(signedToken, {
        pathname: paidDownload.blob_pathname,
        operation: "get",
        access: "private",
        validUntil: Date.now() + 5 * 60 * 1000,
      });
      return NextResponse.redirect(getDownloadUrl(presignedUrl), {
        status: 307,
        headers: { "Cache-Control": "private, no-store" },
      });
    } catch {
      return NextResponse.json({ error: "Export service is temporarily unavailable." }, { status: 503 });
    }
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
