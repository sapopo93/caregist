/**
 * Shared API error normaliser for form-facing endpoints.
 *
 * FastAPI/pydantic returns `detail` in three shapes:
 *   1. string                       — e.g. "Invalid email or password."
 *   2. array of validation objects  — e.g. [{ loc: ["body","email"], msg: "…", type: "value_error" }]
 *   3. missing / non-JSON body      — proxies and 5xx pages often return HTML or nothing
 *
 * This helper converts all three into a single user-safe message plus
 * machine-readable metadata so callers never have to re-implement shape checks.
 */

export interface PydanticErrorItem {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

export interface ApiErrorInfo {
  /** The HTTP status code from the Response. */
  status: number;
  /** Normalised human-readable message. */
  message: string;
  /** True when the body contained the exact unverified-email signal. */
  isUnverifiedEmail: boolean;
  /** True when the server failed (5xx) or the body was not parseable JSON. */
  isServerError: boolean;
  /** True when the caller hit a rate limit. */
  isRateLimited: boolean;
  /** True when the resource already exists (HTTP 409). */
  isConflict: boolean;
}

/** Exact backend message we treat as the email-not-verified signal. */
const UNVERIFIED_EMAIL_DETAIL = "Verify your email before logging in.";

function formatValidationItem(item: PydanticErrorItem): string {
  const msg = String(item.msg ?? "").trim();
  if (!msg) return "";
  const field = Array.isArray(item.loc) && item.loc.length > 1 ? String(item.loc[item.loc.length - 1]) : "";
  return field ? `${field}: ${msg}` : msg;
}

/**
 * Normalise an already-parsed response body into ApiErrorInfo.
 * The caller reads res.json() exactly once (Response bodies are single-use
 * streams) and passes the result here.
 */
export function normalizeApiError(status: number, data: unknown, fallback: string): ApiErrorInfo {
  const info: ApiErrorInfo = {
    status,
    message: fallback,
    isUnverifiedEmail: false,
    isServerError: status >= 500,
    isRateLimited: status === 429,
    isConflict: status === 409,
  };

  // 5xx — never blame the user's input for a server failure.
  if (info.isServerError) {
    info.message = "Our service is temporarily unavailable. Please try again in a few minutes.";
    return info;
  }

  const detail: unknown = (data as Record<string, unknown> | null)?.detail;

  if (typeof detail === "string" && detail.trim()) {
    info.message = detail;
    info.isUnverifiedEmail = detail === UNVERIFIED_EMAIL_DETAIL;
    return info;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const parts = detail.map((item) => formatValidationItem(item as PydanticErrorItem)).filter(Boolean);
    if (parts.length > 0) {
      info.message = parts.join("; ");
      return info;
    }
  }

  return info;
}

/**
 * Parse a fetch Response body into a normalised ApiErrorInfo.
 * Only valid when the caller has NOT already consumed res.json().
 * If you need the body for the success path too, read it once yourself
 * and call normalizeApiError instead.
 */
export async function parseApiError(res: Response, fallback: string): Promise<ApiErrorInfo> {
  const data = await res.json().catch(() => ({}));
  return normalizeApiError(res.status, data, fallback);
}

/**
 * Distinguish a network-level failure (no response at all) from an
 * application-level error that merely threw somewhere unexpected.
 */
export function describeFetchError(err: unknown): string {
  if (err instanceof TypeError && err.message === "Failed to fetch") {
    return "Network error. Please check your connection and try again.";
  }
  return "Something went wrong. Please try again.";
}

type ErrorObject = Record<string, unknown>;

function legacyMessageFromDetail(detail: unknown): string | undefined {
  if (typeof detail === "string" && detail.trim()) return detail.trim();

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (item && typeof item === "object") {
          const message = (item as ErrorObject).msg;
          return typeof message === "string" ? message.trim() : "";
        }
        return "";
      })
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }

  if (detail && typeof detail === "object") {
    const message = (detail as ErrorObject).message;
    if (typeof message === "string" && message.trim()) return message.trim();
  }

  return undefined;
}

/** Compatibility adapter for forms not yet migrated to structured errors. */
export function apiErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const detail = (payload as ErrorObject).detail;
    return legacyMessageFromDetail(detail) ?? fallback;
  }
  return legacyMessageFromDetail(payload) ?? fallback;
}
