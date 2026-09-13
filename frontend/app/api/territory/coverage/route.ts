import { NextResponse } from "next/server";

import { getTerritoryScopeCoverage } from "@/lib/directory-db";
import { releaseGitSha } from "@/lib/release";
import {
  evaluateTerritoryCoverage,
  normalizeTerritoryScope,
  TERRITORY_BRIEF_PRICE_GBP,
} from "@/lib/territory-scope";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "Cache-Control": "private, no-store" } as const;

/**
 * Self-serve scope check for the Territory Opportunity Brief.
 *
 * Body: { region: string, buyerType: string, serviceType?: string }
 * Returns a coverage verdict computed live from the CQC directory record, so a
 * client can confirm their own scope without a scoping call.
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Send a JSON body with region and buyerType." },
      { status: 400, headers: NO_STORE },
    );
  }

  const input = (body ?? {}) as Record<string, unknown>;

  let scope;
  try {
    scope = normalizeTerritoryScope({
      region: typeof input.region === "string" ? input.region : "",
      buyerType: typeof input.buyerType === "string" ? input.buyerType : "",
      serviceType: typeof input.serviceType === "string" ? input.serviceType : "",
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Invalid scope." },
      { status: 400, headers: NO_STORE },
    );
  }

  let coverageRow;
  try {
    coverageRow = await getTerritoryScopeCoverage({
      region: scope.region,
      serviceType: scope.serviceType,
      opportunity: scope.buyerType,
    });
  } catch {
    return NextResponse.json(
      { error: "The directory record is temporarily unavailable. No payment has been taken. Try again shortly." },
      { status: 503, headers: NO_STORE },
    );
  }

  const mostRecentObservation =
    [coverageRow.mostRecentInspection, coverageRow.mostRecentRegistration]
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1) ?? null;

  const result = evaluateTerritoryCoverage(scope, {
    providerCount: coverageRow.providerCount,
    mostRecentObservation,
  });

  return NextResponse.json(
    {
      scope,
      coverage: result,
      price: { currency: "GBP", amount: TERRITORY_BRIEF_PRICE_GBP },
      checkedAt: new Date().toISOString(),
      release: { gitSha: releaseGitSha() },
    },
    { headers: NO_STORE },
  );
}
