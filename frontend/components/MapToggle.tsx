"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

interface Provider {
  slug: string;
  name: string;
  town: string;
  overall_rating: string;
  latitude: number | string;
  longitude: number | string;
  type: string;
}

export default function MapToggle({ providers }: { providers: Provider[] }) {
  const [showMap, setShowMap] = useState(false);

  const hasCoords = providers.some((p) => p.latitude && Number(p.latitude) !== 0);

  if (!hasCoords) return null;

  return (
    <div className="mb-4">
      <button
        onClick={() => setShowMap(!showMap)}
        className="text-sm px-4 py-2 rounded-lg border border-stone text-dusk hover:border-clay hover:text-clay transition-colors"
      >
        {showMap ? "Hide map" : "Show map"}
      </button>
      {showMap && (
        <div className="mt-4">
          <MapView providers={providers} />
        </div>
      )}
    </div>
  );
}
