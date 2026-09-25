import { NextResponse } from "next/server";

import {
  createTerritoryScopeRequest,
  getTerritoryScopeCoverage,
  recordTerritoryScopeRequestAttempt,
  TerritoryScopeRequestRateLimitError,
} from "@/lib/directory-db";
import {
  evaluateTerritoryCoverage,
  normalizeTerritoryScope,
} from "@/lib/territory-scope";
import {
  createTerritoryScopeRequestSecurityIdentity,
  normalizeTerritoryScopeRequestContact,
  TerritoryScopeRequestInputError,
} from "@/lib/territory-scope-request";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "Cache-Control": "private, no-store" } as const;

export async function POST(request: Request) {
  let input: Record<string, unknown>;
  try {
    input = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Send a JSON request." }, { status: 400, headers: NO_STORE });
  }

  let scope;
  let contact;
  try {
    scope = normalizeTerritoryScope({
      region: typeof input.region === "string" ? input.region : "",
      buyerType: typeof input.buyerType === "string" ? input.buyerType : "",
      serviceType: typeof input.serviceType === "string" ? input.serviceType : "",
    });
    contact = normalizeTerritoryScopeRequestContact(input);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Invalid request." },
      { status: 400, headers: NO_STORE },
    );
  }

  try {
    const securityIdentity = createTerritoryScopeRequestSecurityIdentity(request, {
      ...contact,
      region: scope.region,
      buyerType: scope.buyerType,
      serviceType: scope.serviceType,
    });
    const duplicate = await recordTerritoryScopeRequestAttempt(securityIdentity);
    if (duplicate) {
      return NextResponse.json(
        {
          ...duplicate,
          status: "requested",
          duplicate: true,
          message: "Scope request already recorded. No order has been placed and no payment has been taken.",
          checkoutEligible: false,
        },
        { status: 200, headers: NO_STORE },
      );
    }

    // Recompute server-side at intake; never persist browser-supplied counts.
    const coverageRow = await getTerritoryScopeCoverage({
      region: scope.region,
      serviceType: scope.serviceType,
      opportunity: scope.buyerType,
    });
    const mostRecentObservation = [
      coverageRow.mostRecentInspection,
      coverageRow.mostRecentRegistration,
    ]
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1) ?? null;
    const coverage = evaluateTerritoryCoverage(scope, {
      locationCount: coverageRow.locationCount,
      providerOrganisationCount: coverageRow.providerOrganisationCount,
      mostRecentObservation,
    });
    const recorded = await createTerritoryScopeRequest({
      contactEmail: contact.email,
      contactName: contact.name,
      companyName: contact.company,
      region: scope.region,
      buyerType: scope.buyerType,
      serviceType: scope.serviceType,
      locationCount: coverage.locationCount,
      providerOrganisationCount: coverage.providerOrganisationCount,
      coverageVerdict: coverage.verdict,
      coverageSufficient: coverage.coverageSufficient,
      requesterFingerprint: securityIdentity.requesterFingerprint,
      submissionKey: securityIdentity.submissionKey,
    });

    return NextResponse.json(
      {
        ...recorded,
        message: "Scope request recorded for review. No order has been placed and no payment has been taken.",
        checkoutEligible: false,
      },
      { status: recorded.duplicate ? 200 : 201, headers: NO_STORE },
    );
  } catch (error) {
    if (error instanceof TerritoryScopeRequestInputError) {
      return NextResponse.json({ error: error.message }, { status: 400, headers: NO_STORE });
    }
    if (error instanceof TerritoryScopeRequestRateLimitError) {
      return NextResponse.json(
        { error: "Too many scope requests. Try again later." },
        { status: 429, headers: { ...NO_STORE, "Retry-After": "3600" } },
      );
    }
    return NextResponse.json(
      { error: "We could not record the scope request. No order has been placed. Try again shortly." },
      { status: 503, headers: NO_STORE },
    );
  }
}
