/**
 * Keep only utm_* parameters so tokens or emails in a query string
 * (password reset, email verification) never reach the analytics service.
 */
export function redactAnalyticsUrl(raw: string): string {
  try {
    const url = new URL(raw);
    const kept = new URLSearchParams();
    url.searchParams.forEach((value, key) => {
      if (key.toLowerCase().startsWith("utm_")) kept.append(key, value);
    });
    const query = kept.toString();
    return `${url.origin}${url.pathname}${query ? `?${query}` : ""}`;
  } catch {
    return raw.split(/[?#]/)[0];
  }
}
