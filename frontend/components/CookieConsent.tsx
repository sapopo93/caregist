"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const bannerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const consent = localStorage.getItem("caregist_cookie_consent");
    if (!consent) setVisible(true);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (!visible || !bannerRef.current) {
      root.style.removeProperty("--cookie-consent-offset");
      return;
    }

    const banner = bannerRef.current;
    const reserveBannerSpace = () => {
      root.style.setProperty(
        "--cookie-consent-offset",
        `${Math.ceil(banner.getBoundingClientRect().height)}px`,
      );
    };
    reserveBannerSpace();

    const observer = new ResizeObserver(reserveBannerSpace);
    observer.observe(banner);
    window.addEventListener("resize", reserveBannerSpace);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", reserveBannerSpace);
      root.style.removeProperty("--cookie-consent-offset");
    };
  }, [visible]);

  function dismiss() {
    localStorage.setItem("caregist_cookie_consent", "essential_only");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      ref={bannerRef}
      role="dialog"
      aria-label="Cookie choices"
      className="fixed bottom-0 left-0 right-0 z-50 bg-bark text-cream px-4 py-2 shadow-lg print:hidden"
    >
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="flex-1 text-sm">
          <p>
            We use strictly necessary storage for sign-in, security, and requested preferences. We do not use advertising cookies.
            Read our{" "}
            <Link href="/cookies" className="text-amber underline">cookie policy</Link>.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={dismiss}
            className="px-5 py-2 bg-clay text-white rounded-lg text-sm font-medium hover:bg-amber transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
