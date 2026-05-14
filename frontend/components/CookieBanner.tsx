"use client";

/**
 * CookieBanner — UK PECR-compliant in-house consent banner.
 *
 * Three categories:
 *  - Strictly necessary  (always on; session cookie, CSRF)
 *  - Functional          (third-party scripts such as Sentry; default OFF)
 *  - Analytics           (placeholder for future use; default OFF)
 *
 * Consent is persisted in a first-party cookie `caregist_consent_v1`
 * (1-year expiry, JSON: { functional: bool, analytics: bool, ts: ISO }).
 *
 * References: UK PECR (SI 2003/2426) and ICO cookie guidance.
 * See our privacy policy at /privacy.
 */

import { useState, useEffect, useCallback } from "react";
import { setConsent, getConsentFromCookie } from "@/lib/consent";

interface CookieBannerProps {
  /** Pass true to force the banner open regardless of existing consent
   *  (used by the "Cookie settings" footer link via state lifted to layout). */
  forceOpen?: boolean;
  onClose?: () => void;
}

export default function CookieBanner({ forceOpen, onClose }: CookieBannerProps) {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [functional, setFunctional] = useState(false);
  const [analytics, setAnalytics] = useState(false);

  useEffect(() => {
    if (forceOpen) {
      // Re-opening from footer "Cookie settings" link
      const existing = getConsentFromCookie();
      if (existing) {
        setFunctional(existing.functional);
        setAnalytics(existing.analytics);
      }
      setVisible(true);
      return;
    }
    // Show on first visit only
    const existing = getConsentFromCookie();
    if (!existing) {
      setVisible(true);
    }
  }, [forceOpen]);

  const close = useCallback(() => {
    setVisible(false);
    onClose?.();
  }, [onClose]);

  function handleAcceptAll() {
    setConsent(true, true);
    close();
  }

  function handleRejectNonEssential() {
    setConsent(false, false);
    close();
  }

  function handleSavePreferences() {
    setConsent(functional, analytics);
    close();
  }

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cookie consent"
      className="fixed bottom-0 left-0 right-0 z-[9999] bg-white border-t border-gray-200 shadow-2xl"
    >
      <div className="max-w-5xl mx-auto px-4 py-5 sm:px-6">
        {/* Headline row */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-base font-semibold text-gray-900">
              Your cookie choices
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              We use cookies to keep the site secure and to understand how it is
              used. Under UK PECR we need your consent before setting any
              non-essential cookies. See our{" "}
              <a
                href="/privacy"
                className="underline hover:text-blue-700"
              >
                privacy policy
              </a>{" "}
              and{" "}
              <a
                href="/cookies"
                className="underline hover:text-blue-700"
              >
                cookie policy
              </a>{" "}
              for full details.
            </p>
          </div>
        </div>

        {/* Toggle details */}
        <button
          type="button"
          onClick={() => setShowDetails((v) => !v)}
          className="mt-3 text-sm text-blue-600 underline hover:text-blue-800 focus:outline-none"
          aria-expanded={showDetails}
        >
          {showDetails ? "Hide details" : "Manage preferences"}
        </button>

        {showDetails && (
          <div className="mt-4 space-y-3 border border-gray-100 rounded-md p-4 bg-gray-50">
            {/* Strictly necessary */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Strictly necessary
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Session management and CSRF protection. Cannot be disabled.
                </p>
              </div>
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide mt-0.5">
                Always on
              </span>
            </div>

            {/* Functional */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Functional
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Error monitoring (Sentry) and other third-party services that
                  improve site reliability. Loaded only after consent.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer mt-0.5">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={functional}
                  onChange={(e) => setFunctional(e.target.checked)}
                  aria-label="Functional cookies"
                />
                <div className="w-10 h-5 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-2 peer-focus:ring-blue-300 transition-colors" />
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
              </label>
            </div>

            {/* Analytics */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">
                  Analytics
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Usage analytics to help us improve the product. Currently no
                  analytics scripts are loaded — placeholder for future use.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer mt-0.5">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={analytics}
                  onChange={(e) => setAnalytics(e.target.checked)}
                  aria-label="Analytics cookies"
                />
                <div className="w-10 h-5 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-2 peer-focus:ring-blue-300 transition-colors" />
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
              </label>
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleAcceptAll}
            className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Accept all
          </button>
          <button
            type="button"
            onClick={handleRejectNonEssential}
            className="inline-flex items-center px-4 py-2 rounded-md bg-gray-100 text-gray-800 text-sm font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Reject non-essential
          </button>
          {showDetails && (
            <button
              type="button"
              onClick={handleSavePreferences}
              className="inline-flex items-center px-4 py-2 rounded-md border border-blue-600 text-blue-600 text-sm font-medium hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              Save preferences
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
