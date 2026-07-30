import { NextRequest, NextResponse } from "next/server";

import { canIssueDirectoryAccessTokens, createDirectoryAccessToken } from "@/lib/directory-access-token";
import { createLeadAndToken } from "@/lib/directory-db";
import { classifyDirectoryDatabaseError } from "@/lib/directory-db-status";
import { sendLeadNotification } from "@/lib/directory-lead-notify";
import { normalizeLeadRequest, type NormalizedLeadRequest } from "@/lib/directory-leads";

export const runtime = "nodejs";

function setScopeParams(url: URL, scope: { region: string; serviceType: string; rating: string; opportunity?: string }) {
  if (scope.region) url.searchParams.set("region", scope.region);
  if (scope.serviceType) url.searchParams.set("service_type", scope.serviceType);
  if (scope.rating) url.searchParams.set("rating", scope.rating);
  if (scope.opportunity) url.searchParams.set("opportunity", scope.opportunity);
}

async function redirectWithStatelessToken(
  redirectUrl: URL,
  normalized: NormalizedLeadRequest,
  failureReason: string,
) {
  if (!canIssueDirectoryAccessTokens()) {
    throw new Error("DIRECTORY_TOKEN_SECRET is required for opportunity-scoped lead exports.");
  }

  const token = createDirectoryAccessToken(normalized);

  try {
    const delivered = await sendLeadNotification(normalized, {
      mode: "stateless",
      failureReason,
    });

    if (!delivered) {
      console.error("Lead notification email is not configured; falling back to application logs.", {
        region: normalized.region,
        serviceType: normalized.serviceType,
        rating: normalized.rating,
        opportunity: normalized.opportunity,
        failureReason,
      });
    }
  } catch (notifyError) {
    console.error("Lead notification delivery failed.", {
      region: normalized.region,
      serviceType: normalized.serviceType,
      rating: normalized.rating,
      opportunity: normalized.opportunity,
      failureReason,
      errorType: notifyError instanceof Error ? notifyError.name : "UnknownError",
    });
  }

  redirectUrl.searchParams.set("submitted", "1");
  redirectUrl.searchParams.set("token", token);
  redirectUrl.searchParams.set("mode", "stateless");
  setScopeParams(redirectUrl, normalized);

  return NextResponse.redirect(redirectUrl, 303);
}

export async function POST(request: NextRequest) {
  if (process.env.DIRECTORY_LEAD_INTAKE_ENABLED !== "true") {
    const holdUrl = new URL("/lead-list", request.url);
    holdUrl.searchParams.set("hold", "human-gate");
    return NextResponse.redirect(holdUrl, 303);
  }

  const formData = await request.formData();
  const input = {
    email: String(formData.get("email") ?? ""),
    region: String(formData.get("region") ?? ""),
    serviceType: String(formData.get("service_type") ?? ""),
    rating: String(formData.get("rating") ?? ""),
    opportunity: String(formData.get("opportunity") ?? ""),
  };

  const redirectUrl = new URL("/lead-list", request.url);

  try {
    const normalized = normalizeLeadRequest(input);
    if (normalized.opportunity) {
      return redirectWithStatelessToken(
        redirectUrl,
        normalized,
        "Opportunity-specific scopes are issued as signed stateless export tokens.",
      );
    }

    try {
      const { token } = await createLeadAndToken(normalized);

      redirectUrl.searchParams.set("submitted", "1");
      redirectUrl.searchParams.set("token", token);
      redirectUrl.searchParams.set("mode", "database");
      setScopeParams(redirectUrl, normalized);

      return NextResponse.redirect(redirectUrl, 303);
    } catch (error) {
      const failureReason = classifyDirectoryDatabaseError(error);
      return redirectWithStatelessToken(redirectUrl, normalized, failureReason);
    }
  } catch (error) {
    setScopeParams(redirectUrl, input);
    redirectUrl.searchParams.set(
      "error",
      error instanceof Error && /(email is required|valid email|email is too long|filter is too long|choose at least one)/i.test(error.message)
        ? error.message
        : "We could not create your lead request. Please try again shortly.",
    );
    return NextResponse.redirect(redirectUrl, 303);
  }
}
