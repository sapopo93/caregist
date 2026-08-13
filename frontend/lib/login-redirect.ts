const ALLOWED_LOGIN_DESTINATIONS = [
  "/dashboard",
  "/provider-dashboard",
  "/admin",
  "/crm",
] as const;

/** Keep post-login navigation same-origin and limited to protected CareGist workspaces. */
export function normalizeLoginRedirect(value: string | null): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return null;
  }
  try {
    const base = "https://caregist.local";
    const parsed = new URL(value, base);
    if (parsed.origin !== base) return null;
    const permitted = ALLOWED_LOGIN_DESTINATIONS.some(
      (path) => parsed.pathname === path || parsed.pathname.startsWith(`${path}/`),
    );
    return permitted ? `${parsed.pathname}${parsed.search}` : null;
  } catch {
    return null;
  }
}
