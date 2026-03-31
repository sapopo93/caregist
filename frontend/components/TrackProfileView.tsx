"use client";

import { useEffect } from "react";

export default function TrackProfileView({ slug }: { slug: string }) {
  useEffect(() => {
    fetch(`/api/v1/track/profile-view`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug }),
    }).catch(() => {});
  }, [slug]);

  return null;
}
