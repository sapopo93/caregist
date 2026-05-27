/**
 * consent.ts — Caregist consent utilities
 *
 * Cookie name : caregist_consent_v1
 * Payload     : { functional: boolean, analytics: boolean, ts: string }
 * Expiry      : 1 year (PECR allows up to 12 months between re-prompts)
 *
 * Audit event : COOKIE_CONSENT_RECORDED
 *   Written with a SHA-256 hash of the consent JSON + timestamp. No PII.
 *
 * References:
 *   - UK PECR (SI 2003/2426) Regulation 6
 *   - ICO cookie guidance (2023) https://ico.org.uk/for-organisations/guide-to-pecr/cookies-and-similar-technologies/
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ConsentPayload {
  functional: boolean;
  analytics: boolean;
  ts: string; // ISO 8601 datetime
}

export interface ConsentState extends ConsentPayload {
  hasConsented: boolean;
}

// ─── Cookie helpers ──────────────────────────────────────────────────────────

const CONSENT_COOKIE = "caregist_consent_v1";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/**
 * Read the consent cookie from document.cookie (client-side only).
 * Returns null if not yet set or if the value is malformed.
 */
export function getConsentFromCookie(): ConsentPayload | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${CONSENT_COOKIE}=`));
  if (!match) return null;
  try {
    const raw = decodeURIComponent(match.slice(CONSENT_COOKIE.length + 1));
    const parsed = JSON.parse(raw) as ConsentPayload;
    if (
      typeof parsed.functional === "boolean" &&
      typeof parsed.analytics === "boolean" &&
      typeof parsed.ts === "string"
    ) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Write the consent cookie (client-side).
 * SameSite=Lax; Secure; 1-year expiry.
 */
function writeConsentCookie(payload: ConsentPayload): void {
  const encoded = encodeURIComponent(JSON.stringify(payload));
  const expires = new Date(Date.now() + ONE_YEAR_SECONDS * 1000).toUTCString();
  // Note: HttpOnly cannot be set from JS — this is a first-party consent cookie
  // that deliberately needs to be JS-readable so the banner can inspect it.
  document.cookie = [
    `${CONSENT_COOKIE}=${encoded}`,
    `expires=${expires}`,
    "path=/",
    "SameSite=Lax",
    "Secure",
  ].join("; ");
}

// ─── Audit log ───────────────────────────────────────────────────────────────

/**
 * Compute a deterministic SHA-256 hex digest of the consent payload.
 * No PII — only the boolean choices + timestamp.
 */
async function hashConsent(payload: ConsentPayload): Promise<string> {
  const text = JSON.stringify({
    functional: payload.functional,
    analytics: payload.analytics,
    ts: payload.ts,
  });
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(text),
  );
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Emit COOKIE_CONSENT_RECORDED audit event.
 * Sends to /api/audit-log (fire-and-forget; failures are non-fatal).
 */
async function emitAuditEvent(payload: ConsentPayload): Promise<void> {
  try {
    const hash = await hashConsent(payload);
    await fetch("/api/audit-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event: "COOKIE_CONSENT_RECORDED",
        consentHash: hash,
        ts: payload.ts,
      }),
      // keepalive so the request survives navigation
      keepalive: true,
    });
  } catch {
    // Non-fatal — audit failure must not break consent flow
    if (process.env.NODE_ENV !== "production") {
      console.warn("[caregist] Audit log emit failed (non-fatal)");
    }
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * setConsent — writes the consent cookie and emits an audit log event.
 * Call from CookieBanner action buttons.
 */
export function setConsent(functional: boolean, analytics: boolean): void {
  const payload: ConsentPayload = {
    functional,
    analytics,
    ts: new Date().toISOString(),
  };
  writeConsentCookie(payload);
  // Emit audit event asynchronously; do not block UI
  void emitAuditEvent(payload);
}

// ─── React hook ──────────────────────────────────────────────────────────────

import { useState, useEffect } from "react";

/**
 * useConsent() — React hook that reads `caregist_consent_v1` cookie.
 *
 * Returns { functional, analytics, hasConsented }.
 * Re-evaluates on mount only (cookie changes during a session are rare;
 * full re-reads happen when the banner re-renders after save).
 */
export function useConsent(): ConsentState {
  const [state, setState] = useState<ConsentState>({
    functional: false,
    analytics: false,
    hasConsented: false,
  });

  useEffect(() => {
    const payload = getConsentFromCookie();
    if (payload) {
      setState({
        functional: payload.functional,
        analytics: payload.analytics,
        hasConsented: true,
      });
    }
  }, []);

  return state;
}

// ─── Server-side RSC helper ───────────────────────────────────────────────────

/**
 * getConsent(cookies) — server-side helper for React Server Components.
 *
 * Usage (RSC):
 *   import { cookies } from "next/headers";
 *   import { getConsent } from "@/lib/consent";
 *   const consent = getConsent(cookies());
 *
 * @param cookieStore  Next.js ReadonlyRequestCookies from `next/headers`
 */
export function getConsent(
  cookieStore: { get(name: string): { value: string } | undefined },
): ConsentState {
  const cookie = cookieStore.get(CONSENT_COOKIE);
  if (!cookie) {
    return { functional: false, analytics: false, hasConsented: false };
  }
  try {
    const raw = decodeURIComponent(cookie.value);
    const parsed = JSON.parse(raw) as ConsentPayload;
    if (
      typeof parsed.functional === "boolean" &&
      typeof parsed.analytics === "boolean"
    ) {
      return { ...parsed, hasConsented: true };
    }
    return { functional: false, analytics: false, hasConsented: false };
  } catch {
    return { functional: false, analytics: false, hasConsented: false };
  }
}
