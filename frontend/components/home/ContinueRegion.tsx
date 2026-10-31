"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LAST_REGION_EVENT, forgetRegion, readLastRegion } from "@/lib/last-region";

/** "Continue with London": a shortcut back into the territory check for the region this visitor last looked at. */
export default function ContinueRegion() {
  const [region, setRegion] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setRegion(readLastRegion());
    sync();
    window.addEventListener(LAST_REGION_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(LAST_REGION_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (!region) return null;

  return (
    <p className="mt-4 flex flex-wrap items-center gap-x-3 text-sm text-dusk">
      <span>Last time you looked at</span>
      <Link
        href={`/pricing/territory?region=${encodeURIComponent(region)}`}
        className="font-semibold text-clay underline underline-offset-4 hover:text-bark"
      >
        {region}: continue the territory check →
      </Link>
      <button type="button" onClick={forgetRegion} className="text-xs underline underline-offset-2 hover:text-bark">
        Forget
      </button>
    </p>
  );
}
