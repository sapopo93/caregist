export const RECENT_KEY = "caregist_recent_providers";
export const RECENT_EVENT = "caregist:recent-updated";
const MAX_RECENT = 6;

export interface RecentProvider {
  href: string;
  name: string;
  rating: string | null;
  place: string;
}

export function readRecent(): RecentProvider[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(parsed)
      ? parsed.filter((p) => p && typeof p.href === "string" && p.href.startsWith("/provider/") && typeof p.name === "string").slice(0, MAX_RECENT)
      : [];
  } catch {
    return [];
  }
}

export function rememberProvider(entry: RecentProvider) {
  try {
    const next = [entry, ...readRecent().filter((p) => p.href !== entry.href)].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
    window.dispatchEvent(new Event(RECENT_EVENT));
  } catch {
    // Storage unavailable (private mode, blocked): the convenience simply does not appear.
  }
}

export function clearRecent() {
  try {
    localStorage.removeItem(RECENT_KEY);
    window.dispatchEvent(new Event(RECENT_EVENT));
  } catch {
    // ignore
  }
}
