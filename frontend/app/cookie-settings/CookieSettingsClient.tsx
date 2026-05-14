"use client";

/**
 * CookieSettingsClient — interactive preferences form for /cookie-settings.
 * Reads existing consent from the cookie, allows granular toggling, and
 * saves via setConsent().
 */

import { useState, useEffect } from "react";
import { getConsentFromCookie, setConsent } from "@/lib/consent";

export default function CookieSettingsClient() {
  const [functional, setFunctional] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const existing = getConsentFromCookie();
    if (existing) {
      setFunctional(existing.functional);
      setAnalytics(existing.analytics);
    }
  }, []);

  function handleSave() {
    setConsent(functional, analytics);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  function handleAcceptAll() {
    setFunctional(true);
    setAnalytics(true);
    setConsent(true, true);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  function handleRejectAll() {
    setFunctional(false);
    setAnalytics(false);
    setConsent(false, false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="space-y-6">
      {/* Strictly necessary */}
      <div className="border border-gray-200 rounded-lg p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Strictly necessary</h2>
            <p className="mt-1 text-xs text-gray-500">
              Required for the site to function. Includes session management and
              CSRF protection cookies. These cannot be disabled under PECR because
              they are essential for a service explicitly requested by you.
            </p>
          </div>
          <span className="ml-4 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
            Always on
          </span>
        </div>
      </div>

      {/* Functional */}
      <div className="border border-gray-200 rounded-lg p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 mr-4">
            <h2 className="text-sm font-semibold text-gray-900">Functional</h2>
            <p className="mt-1 text-xs text-gray-500">
              Third-party services that improve site reliability and your
              experience. Currently includes: Sentry error monitoring.
              These scripts are only loaded after your consent.
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer mt-1">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={functional}
              onChange={(e) => setFunctional(e.target.checked)}
              aria-label="Allow functional cookies"
            />
            <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-2 peer-focus:ring-blue-300 transition-colors" />
            <div className="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
          </label>
        </div>
      </div>

      {/* Analytics */}
      <div className="border border-gray-200 rounded-lg p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 mr-4">
            <h2 className="text-sm font-semibold text-gray-900">Analytics</h2>
            <p className="mt-1 text-xs text-gray-500">
              Usage analytics to help us understand how CareGist is used and
              improve the product. No analytics scripts are currently active —
              this category is reserved for future use. Your preference is saved
              so you do not need to be asked again when analytics are introduced.
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer mt-1">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={analytics}
              onChange={(e) => setAnalytics(e.target.checked)}
              aria-label="Allow analytics cookies"
            />
            <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-2 peer-focus:ring-blue-300 transition-colors" />
            <div className="absolute left-0.5 top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
          </label>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="button"
          onClick={handleSave}
          className="px-5 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Save preferences
        </button>
        <button
          type="button"
          onClick={handleAcceptAll}
          className="px-5 py-2 rounded-md bg-gray-100 text-gray-800 text-sm font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400"
        >
          Accept all
        </button>
        <button
          type="button"
          onClick={handleRejectAll}
          className="px-5 py-2 rounded-md bg-gray-100 text-gray-800 text-sm font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400"
        >
          Reject non-essential
        </button>
      </div>

      {saved && (
        <p role="status" className="text-sm text-green-700 font-medium">
          Your preferences have been saved.
        </p>
      )}
    </div>
  );
}
