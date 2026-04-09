"use client";

import { useEffect } from "react";

import { trackEvent } from "@/lib/analytics";

export default function TrackEventOnMount({
  eventType,
  eventSource,
  meta,
}: {
  eventType: string;
  eventSource: string;
  meta?: Record<string, string | number | boolean | null | undefined>;
}) {
  useEffect(() => {
    void trackEvent(eventType, eventSource, meta);
  }, [eventSource, eventType, meta]);

  return null;
}
