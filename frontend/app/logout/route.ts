import { NextResponse } from 'next/server';

/**
 * POST /logout
 * Calls the backend logout endpoint (which revokes the session row),
 * then clears the caregist_session cookie client-side via Set-Cookie.
 * Redirects to / on success.
 *
 * DEPENDENCY: Spool's PR must merge first — the backend validates the
 * cookie and exposes POST /api/v1/auth/logout.
 */
export async function POST(request: Request) {
  // Forward the session cookie to the backend so it can revoke the row.
  const cookieHeader = request.headers.get('cookie') ?? '';

  try {
    await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ''}/api/v1/auth/logout`,
      {
        method: 'POST',
        headers: { cookie: cookieHeader },
        credentials: 'include',
      }
    );
  } catch {
    // Best-effort: even if backend is unreachable, still clear the cookie.
  }

  const response = NextResponse.redirect(new URL('/', request.url));
  response.headers.set(
    'Set-Cookie',
    'caregist_session=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax'
  );
  return response;
}
