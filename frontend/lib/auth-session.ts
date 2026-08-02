"use client";

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
  await fetch("/api/v1/auth/session", { method: "DELETE", credentials: "include" }).catch(() => {});
  localStorage.removeItem("caregist_user");
  localStorage.removeItem("caregist_tier");
  window.dispatchEvent(new Event("caregist_auth_change"));
}
