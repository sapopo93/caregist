/**
 * /app/api/csp-report/route.ts
 *
 * Accepts CSP violation reports (Content-Security-Policy-Report-Only or
 * enforcing). Reports are forwarded to Sentry (if functional consent is
 * available server-side) or logged to stdout for now.
 *
 * Returns 204 No Content as required by the CSP spec.
 *
 * Reference: https://www.w3.org/TR/CSP3/#report-violation
 */

import { NextRequest, NextResponse } from "next/server";

interface CspReport {
  "csp-report"?: {
    "document-uri"?: string;
    referrer?: string;
    "violated-directive"?: string;
    "effective-directive"?: string;
    "original-policy"?: string;
    "blocked-uri"?: string;
    "status-code"?: number;
    "source-file"?: string;
    "line-number"?: number;
    "column-number"?: number;
  };
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  try {
    const body = (await req.json()) as CspReport;
    const report = body["csp-report"];
    if (report) {
      // Log key fields only — omit full original-policy to keep logs readable.
      console.warn("[caregist:csp-violation]", {
        blockedUri: report["blocked-uri"],
        violatedDirective: report["violated-directive"],
        effectiveDirective: report["effective-directive"],
        documentUri: report["document-uri"],
        sourceFile: report["source-file"],
        lineNumber: report["line-number"],
        statusCode: report["status-code"],
        ts: new Date().toISOString(),
      });

      // TODO: forward to Sentry as a breadcrumb or custom event once
      // Sentry functional consent is confirmed server-side:
      //   Sentry.captureEvent({ message: "CSP violation", extra: report });
    }
  } catch {
    // Malformed report body — swallow silently; return 204 regardless.
  }

  // CSP spec requires 200-range response. 204 is conventional.
  return new NextResponse(null, { status: 204 });
}
