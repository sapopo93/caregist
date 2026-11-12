"use client";

import { useEffect } from "react";

import { redactAnalyticsUrl } from "@/lib/analytics-url";

type VaEvent = { type: string; url: string };
type VaFunction = ((...args: unknown[]) => void) & { q?: unknown[] };

declare global {
  interface Window {
    va?: VaFunction;
    vaq?: unknown[];
  }
}

/**
 * Vercel Web Analytics: cookieless, aggregated page views served from this
 * origin (/_vercel/insights). Injected from a nonced client bundle, so the
 * 'strict-dynamic' CSP in proxy.ts allows it without loosening script-src.
 * It does nothing until Web Analytics is enabled on the Vercel project.
 */
export default function WebAnalytics() {
  useEffect(() => {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return;
    if (document.querySelector('script[data-caregist-analytics]')) return;

    if (!window.va) {
      window.va = function va(...args: unknown[]) {
        (window.vaq = window.vaq || []).push(args);
      };
    }
    window.va("beforeSend", (event: VaEvent) => ({ ...event, url: redactAnalyticsUrl(event.url) }));

    const script = document.createElement("script");
    script.src = "/_vercel/insights/script.js";
    script.defer = true;
    script.dataset.caregistAnalytics = "1";
    document.head.appendChild(script);
  }, []);

  return null;
}
