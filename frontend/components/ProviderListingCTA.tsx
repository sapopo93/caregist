"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { trackEvent } from "@/lib/analytics";

export default function ProviderListingCTA({
  tier,
  color,
}: {
  tier: "enhanced" | "premium" | "sponsored";
  color: string;
}) {
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    try {
      setLoggedIn(!!localStorage.getItem("caregist_user"));
    } catch {}
  }, []);

  const href = loggedIn
    ? `/search?intent=claim&provider_tier=${tier}`
    : `/signup?provider_tier=${tier}`;

  const label = loggedIn ? "Find your listing" : "Get started";

  return (
    <Link
      href={href}
      className="block text-center py-2.5 rounded-lg text-sm font-medium text-white transition-colors"
      style={{ background: color }}
      onClick={() =>
        void trackEvent("provider_listing_cta_click", "pricing_card", {
          tier,
          auth: loggedIn ? "logged_in" : "logged_out",
        })
      }
    >
      {label}
    </Link>
  );
}
