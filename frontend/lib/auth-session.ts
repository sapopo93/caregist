"use client";

/**
 * Auth state is now carried by the HttpOnly `caregist_session` cookie.
 * The browser sends it automatically on every credentialed request —
 * no localStorage is needed or used for auth tokens.
 *
 * isAuthExpiredResponse: detect 401s that mean the session is gone.
 * clearBrowserAuthState: POST to the logout route which revokes the
 *   server-side session row and clears the cookie via Set-Cookie.
 */

export function isAuthExpiredResponse(status: number, detail?: string) {
  if (status !== 401) return false;
  const normalized = (detail || "").toLowerCase();
  return (
    normalized.includes("session") ||
    normalized.includes("missing api key") ||
    normalized.includes("invalid api key")
  );
}

export async function clearBrowserAuthState() {
  // POST to the Next.js Route Handler which calls backend /api/v1/auth/logout
  // and sets Set-Cookie: caregist_session=; Max-Age=0 to clear the cookie.
  await fetch("/logout", { method: "POST", credentials: "include" }).catch(() => {});
  // Dispatch for any in-page listeners that still need to react
  window.dispatchEvent(new Event("caregist_auth_change"));
}
