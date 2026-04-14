"use client";

import { useEffect } from "react";

export default function WarmingUpBanner() {
  useEffect(() => {
    const t = setTimeout(() => window.location.reload(), 30_000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="bg-cream border border-amber rounded-lg p-6 mb-6 text-center">
      <p className="text-bark font-semibold">The server is waking up</p>
      <p className="text-dusk text-sm mt-1">
        This takes about 30 seconds on first load. Refreshing the page in a moment...
      </p>
    </div>
  );
}
