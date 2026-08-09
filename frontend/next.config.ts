import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

// The legacy standalone API subdomain is retired — Vercel Services now binds
// the frontend to the backend via CAREGIST_BACKEND_URL (see vercel.json), so
// there is no app-URL-derived API host to fall back to.
function resolveApiBaseForProduction(value?: string) {
  return value;
}

function failOrWarn(message: string) {
  if (process.env.NODE_ENV === "production") {
    throw new Error(message);
  }
  console.warn(message);
}

function validateServerApiEnv() {
  const serverApiKey =
    process.env.API_KEY ||
    process.env.API_MASTER_KEY ||
    process.env.NEXT_PUBLIC_API_KEY;

  const serverApiBase =
    process.env.CAREGIST_BACKEND_URL ||
    resolveApiBaseForProduction(process.env.API_URL) ||
    resolveApiBaseForProduction(process.env.NEXT_PUBLIC_API_URL) ||
    process.env.APP_URL ||
    process.env.NEXT_PUBLIC_APP_URL ||
    process.env.VERCEL_PROJECT_PRODUCTION_URL ||
    process.env.VERCEL_URL;

  if (!serverApiBase) {
    failOrWarn(
      "[caregist] Missing API_URL/NEXT_PUBLIC_API_URL/APP_URL. Server-side frontend requests will not know how to reach the API.",
    );
  }

  if (serverApiKey && process.env.API_KEY === "dev_key_change_me") {
    failOrWarn("[caregist] API_KEY is still set to the placeholder dev key.");
  }

  if (serverApiKey && process.env.API_MASTER_KEY === "change_me_in_production") {
    failOrWarn("[caregist] API_MASTER_KEY is still set to the placeholder production value.");
  }

  if (process.env.NEXT_PUBLIC_API_KEY && !process.env.API_KEY && !process.env.API_MASTER_KEY) {
    failOrWarn(
      "[caregist] NEXT_PUBLIC_API_KEY is the only API key set. This exposes credentials in the browser bundle and will break silently after key rotation. Add API_KEY to frontend/.env.local.",
    );
  } else if (process.env.NEXT_PUBLIC_API_KEY) {
    console.warn(
      "[caregist] NEXT_PUBLIC_API_KEY is set alongside API_KEY. Remove it to prevent browser bundle exposure.",
    );
  }
}

validateServerApiEnv();

const nextConfig: NextConfig = {
  devIndicators: false,
  outputFileTracingIncludes: {
    "/": ["./data/directory-fallback-full.csv"],
    "/search": ["./data/directory-fallback-full.csv"],
    "/lead-list": ["./data/directory-fallback-full.csv"],
    "/provider/[slug]": ["./data/directory-fallback-full.csv"],
    "/api/export": ["./data/directory-fallback-full.csv"],
    "/api/health/directory": ["./data/directory-fallback-full.csv"],
    "/api/v1/service-types": ["./data/directory-fallback-full.csv"],
  },
  async rewrites() {
    const apiBase =
      process.env.CAREGIST_BACKEND_URL ||
      resolveApiBaseForProduction(process.env.NEXT_PUBLIC_API_URL) ||
      resolveApiBaseForProduction(process.env.API_URL) ||
      "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
          // Content-Security-Policy is set per-request (with a nonce) in
          // proxy.ts so script-src can drop 'unsafe-inline' (F-21).
        ],
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  sourcemaps: {
    disable: !process.env.SENTRY_AUTH_TOKEN,
  },
});
