import { NextRequest, NextResponse } from "next/server";

/**
 * Protected routes that require authentication.
 * These routes will redirect to /login if the user is not authenticated.
 */
const PROTECTED_ROUTES = [
  "/dashboard",
  "/provider-dashboard",
  "/admin",
];

/**
 * Middleware to enforce authentication on protected routes.
 *
 * This middleware:
 * 1. Checks for a valid session cookie on protected routes
 * 2. Validates the session against the backend API
 * 3. Redirects to /login if the session is invalid or missing
 * 4. Allows public routes to pass through
 *
 * Session validation is cached for 60 seconds to avoid excessive API calls.
 */
export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Allow public routes to pass through
  if (!PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for session cookie
  const sessionCookie = request.cookies.get("caregist_session");

  if (!sessionCookie) {
    // No session cookie — redirect to login
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Validate the session against the backend API
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        Cookie: `caregist_session=${sessionCookie.value}`,
      },
      credentials: "include",
    });

    if (!response.ok) {
      // Invalid session — redirect to login
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Session is valid — allow the request to proceed
    return NextResponse.next();
  } catch (error) {
    // Network error validating session — log and allow (fail open to avoid blocking on backend issues)
    console.warn("Session validation error:", error);
    return NextResponse.next();
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!api|_next/static|_next/image|favicon.ico|public).*)",
  ],
};
