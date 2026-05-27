"use client";

/**
 * CookieBannerRoot — thin client wrapper that mounts CookieBanner and
 * provides the "Cookie settings" footer trigger via a custom event.
 *
 * The footer "Cookies" link navigates to /cookies which renders
 * CookieSettingsPage; this component also listens for a custom DOM event
 * `caregist:reopen-cookie-banner` so that any button/link in the app can
 * trigger the banner programmatically without prop-drilling.
 *
 * Usage from a button:
 *   document.dispatchEvent(new Event("caregist:reopen-cookie-banner"));
 */

import { useState, useEffect } from "react";
import CookieBanner from "@/components/CookieBanner";

export default function CookieBannerRoot() {
  const [forceOpen, setForceOpen] = useState(false);

  useEffect(() => {
    function handleReopen() {
      setForceOpen(true);
    }
    document.addEventListener("caregist:reopen-cookie-banner", handleReopen);
    return () => {
      document.removeEventListener("caregist:reopen-cookie-banner", handleReopen);
    };
  }, []);

  return (
    <CookieBanner
      forceOpen={forceOpen}
      onClose={() => setForceOpen(false)}
    />
  );
}
