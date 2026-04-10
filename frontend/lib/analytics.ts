"use client";

type EventMeta = Record<string, string | number | boolean | null | undefined>;

export async function trackEvent(
  eventType: string,
  eventSource: string,
  meta: EventMeta = {},
) {
  try {
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      if (hostname === "localhost" || hostname === "127.0.0.1") return;
    }

    await fetch("/api/v1/analytics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: eventType,
        event_source: eventSource,
        meta,
      }),
      keepalive: true,
    });
  } catch {
    // Analytics must never block the user flow.
  }
}
