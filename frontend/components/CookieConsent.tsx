"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem("caregist_cookie_consent");
    if (!consent) setVisible(true);
  }, []);

  function accept() {
    localStorage.setItem("caregist_cookie_consent", "accepted");
    setVisible(false);
  }

  function decline() {
    localStorage.setItem("caregist_cookie_consent", "essential_only");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-bark text-cream px-6 py-4 shadow-lg print:hidden">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex-1 text-sm">
          <p>
            We use cookies for site functionality and to analyse traffic.
            Read our{" "}
            <Link href="/cookies" className="text-amber underline">cookie policy</Link>.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={accept}
            className="px-5 py-2 bg-clay text-white rounded-lg text-sm font-medium hover:bg-amber transition-colors"
          >
            Accept all
          </button>
          <button
            onClick={decline}
            className="px-5 py-2 border border-cream/30 text-cream rounded-lg text-sm font-medium hover:bg-cream/10 transition-colors"
          >
            Essential only
          </button>
        </div>
      </div>
    </div>
  );
}
