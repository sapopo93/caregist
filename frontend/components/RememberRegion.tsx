"use client";

import { useEffect } from "react";

import { rememberRegion } from "@/lib/last-region";

/** Renders nothing; records the region being viewed in this browser only. */
export default function RememberRegion({ region }: { region: string }) {
  useEffect(() => {
    rememberRegion(region);
  }, [region]);
  return null;
}
