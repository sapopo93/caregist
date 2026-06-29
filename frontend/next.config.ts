import { withSentryConfig } from "@sentry/nextjs";
import type { NextConfig } from "next";

const apiDestination =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "https://api.caregist.co.uk" : "http://localhost:8000");

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
          // middleware.ts so script-src can drop 'unsafe-inline' (F-21).
        ],
      },
    ];
  },
  async rewrites() {
    return {
      fallback: [
        {
          source: "/api/:path*",
          destination: `${apiDestination}/api/:path*`,
        },
      ],
    };
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
