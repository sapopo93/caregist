import { NextRequest, NextResponse } from "next/server";
import { getServicePage } from "@/lib/service-page-config";

/**
 * Protected routes that require authentication.
 * These routes will redirect to /login if the user is not authenticated.
 */
const PROTECTED_ROUTES = [
  "/dashboard",
  "/provider-dashboard",
  "/admin",
  "/crm",
];

/**
 * Build a per-request Content-Security-Policy with a nonce (F-21).
 *
 * script-src uses a nonce + 'strict-dynamic' instead of 'unsafe-inline', so an
 * injected inline <script> cannot execute. 'strict-dynamic' lets Next's nonced
 * bootstrap scripts load the rest of the bundle. style-src keeps 'unsafe-inline'
 * (Tailwind/Next inject inline styles; style injection is a far lower XSS risk).
 */
function buildCsp(nonce: string, crmVoice = false): string {
  const isDev = process.env.NODE_ENV !== "production";
  const scriptSrc = isDev
    ? `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
    : `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`;
  return [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data:",
    "font-src 'self' https://fonts.gstatic.com",
    crmVoice
      ? "connect-src 'self' https://api.stripe.com https://*.sentry.io https://*.twilio.com wss://*.twilio.com"
      : "connect-src 'self' https://api.stripe.com https://*.sentry.io",
    crmVoice ? "media-src 'self' blob: https://sdk.twilio.com" : "media-src 'self'",
    "frame-src https://js.stripe.com",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}

function withCsp(response: NextResponse, nonce: string, crmVoice = false): NextResponse {
  response.headers.set("Content-Security-Policy", buildCsp(nonce, crmVoice));
  response.headers.set(
    "Permissions-Policy",
    crmVoice ? "camera=(), microphone=(self), geolocation=()" : "camera=(), microphone=(), geolocation=()",
  );
  response.headers.set("x-nonce", nonce);
  return response;
}

/**
 * Middleware: attaches a nonce-based CSP to every response (F-21) and enforces
 * authentication on protected routes (F-2).
 */
export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const crmVoice = pathname.startsWith("/crm");

  // One nonce per request; forwarded to the app so Next applies it to its
  // framework scripts and Server Components can nonce their own inline scripts.
  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = buildCsp(nonce, crmVoice);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  // Next.js reads the nonce from the request's Content-Security-Policy header to
  // automatically stamp it onto its own bootstrap scripts.
  requestHeaders.set("Content-Security-Policy", csp);
  const passThrough = () =>
    withCsp(NextResponse.next({ request: { headers: requestHeaders } }), nonce, crmVoice);
  const redirectToLogin = () => {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return withCsp(NextResponse.redirect(loginUrl), nonce, false);
  };

  // App Router notFound() can return HTTP 200 after a dynamic response starts
  // streaming. Resolve the finite public service taxonomy before rendering so
  // unknown service URLs have an honest HTTP status and retain the standard UI.
  const serviceMatch = pathname.match(/^\/services\/([^/]+)\/?$/);
  if (serviceMatch && !getServicePage(serviceMatch[1])) {
    const notFoundUrl = request.nextUrl.clone();
    notFoundUrl.pathname = "/_caregist-service-not-found";
    notFoundUrl.search = "";
    return withCsp(
      NextResponse.rewrite(notFoundUrl, {
        status: 404,
        request: { headers: requestHeaders },
      }),
      nonce,
      false,
    );
  }

  // Public routes still receive the CSP, but skip the auth check.
  if (!PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
    return passThrough();
  }

  const sessionCookie = request.cookies.get("caregist_session");
  if (!sessionCookie) {
    return redirectToLogin();
  }

  // Validate the session against the backend API.
  try {
    const apiUrl = request.nextUrl.origin;
    const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        Cookie: `caregist_session=${sessionCookie.value}`,
      },
      credentials: "include",
    });

    if (!response.ok) {
      return redirectToLogin();
    }
    return passThrough();
  } catch (error) {
    // Protected routes must fail closed if the session cannot be validated.
    console.warn("Session validation error:", error);
    return redirectToLogin();
  }
}

export const config = {
  matcher: [
    /*
     * Match /api because it is a public marketing page. Exclude API route
     * handlers under /api/* and static/image assets below.
     *
     * Match all request paths except for the ones starting with:
     * - api/ (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/api",
    "/((?!api/|_next/static|_next/image|favicon.ico|public).*)",
  ]
};
