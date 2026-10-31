"use client";

import { useEffect } from "react";

import { rememberProvider, type RecentProvider } from "@/lib/recent-providers";

/** Renders nothing; records this provider in the visitor's own browser for the "pick up where you left off" strip. */
export default function RememberProvider(props: RecentProvider) {
  const { href, name, rating, place } = props;
  useEffect(() => {
    rememberProvider({ href, name, rating, place });
  }, [href, name, rating, place]);
  return null;
}
