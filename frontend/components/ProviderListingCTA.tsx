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
  const [href, setHref] = useState(`/signup?provider_tier=${tier}`);
  const [label, setLabel] = useState("Get started");

  useEffect(() => {
    const stored = localStorage.getItem("caregist_user");
    if (!stored) return;

    setLoggedIn(true);

    fetch("/api/v1/claims/my-providers", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        const providers: { slug: string; name: string; profile_tier: string }[] =
          data.providers || [];
        if (providers.length > 0) {
          setHref(`/provider-dashboard/${providers[0].slug}?upgrade_tier=${tier}`);
          setLabel("Upgrade your listing");
        } else {
          setHref(`/search?claim_intent=${tier}`);
          setLabel("Find your listing");
        }
      })
      .catch(() => {
        setHref(`/search?claim_intent=${tier}`);
        setLabel("Find your listing");
      });
  }, [tier]);

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
