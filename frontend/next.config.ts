import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

function deriveApiBaseFromAppUrl(appUrlRaw?: string) {
  if (!appUrlRaw) return undefined;

  try {
    const appUrl = new URL(appUrlRaw.startsWith("http") ? appUrlRaw : `https://${appUrlRaw}`);
    if (appUrl.hostname === "caregist.co.uk" || appUrl.hostname === "www.caregist.co.uk") {
      return `${appUrl.protocol}//api.caregist.co.uk`;
    }
  } catch {
    return undefined;
  }

  return undefined;
}

function deriveApiBaseFromConfiguredAppUrl() {
  return (
    deriveApiBaseFromAppUrl(process.env.APP_URL) ||
    deriveApiBaseFromAppUrl(process.env.NEXT_PUBLIC_APP_URL) ||
    deriveApiBaseFromAppUrl(process.env.VERCEL_PROJECT_PRODUCTION_URL) ||
    deriveApiBaseFromAppUrl(process.env.VERCEL_URL)
  );
}

function isLocalApiBase(value?: string) {
  if (!value) return false;
  try {
    const url = new URL(value);
    return ["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname);
  } catch {
    return false;
  }
}

function resolveApiBaseForProduction(value?: string) {
  const derivedApiBase = deriveApiBaseFromConfiguredAppUrl();
  if (value && derivedApiBase && isLocalApiBase(value)) {
    console.warn("[caregist] Ignoring localhost API URL for production app URL — deriving API host from app URL.");
    return derivedApiBase;
  }
  return value || derivedApiBase;
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

  if (!serverApiKey) {
    failOrWarn(
      "[caregist] Missing API_KEY/API_MASTER_KEY. Server-rendered search and provider pages will fail authentication.",
    );
  }

  if (process.env.API_KEY === "dev_key_change_me") {
    failOrWarn("[caregist] API_KEY is still set to the placeholder dev key.");
  }

  if (process.env.API_MASTER_KEY === "change_me_in_production") {
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
  transpilePackages: ["@support-platform/ui"],
  async rewrites() {
    const apiBase =
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
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self' https://fonts.gstatic.com",
              "connect-src 'self' https://api.stripe.com https://*.sentry.io",
              "frame-src https://js.stripe.com",
              "object-src 'none'",
              "base-uri 'self'",
            ].join("; "),
          },
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
