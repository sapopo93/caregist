import { DEFAULT_REGION_OPTIONS } from "./directory-constants.ts";

export const LAST_REGION_KEY = "caregist_last_region";
export const LAST_REGION_EVENT = "caregist:last-region";

/** Only a known England region is ever stored or returned. */
export function isKnownRegion(value: unknown): value is string {
  return typeof value === "string" && DEFAULT_REGION_OPTIONS.includes(value);
}

export function readLastRegion(): string | null {
  try {
    const value = localStorage.getItem(LAST_REGION_KEY);
    return isKnownRegion(value) ? value : null;
  } catch {
    return null;
  }
}

export function rememberRegion(region: string) {
  if (!isKnownRegion(region)) return;
  try {
    localStorage.setItem(LAST_REGION_KEY, region);
    window.dispatchEvent(new Event(LAST_REGION_EVENT));
  } catch {
    // Storage unavailable: the shortcut simply does not appear.
  }
}

export function forgetRegion() {
  try {
    localStorage.removeItem(LAST_REGION_KEY);
    window.dispatchEvent(new Event(LAST_REGION_EVENT));
  } catch {
    // ignore
  }
}
