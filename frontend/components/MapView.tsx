"use client";

import { useEffect, useRef } from "react";

interface Provider {
  slug: string;
  name: string;
  town: string;
  overall_rating: string;
  latitude: number | string;
  longitude: number | string;
  type: string;
}

export default function MapView({ providers }: { providers: Provider[] }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current || typeof window === "undefined") return;

    // Dynamically load Leaflet
    const loadMap = async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      if (mapInstance.current) {
        mapInstance.current.remove();
      }

      const validProviders = providers.filter(
        (p) => p.latitude && p.longitude && Number(p.latitude) !== 0
      );

      if (validProviders.length === 0) return;

      const map = L.map(mapRef.current!, { scrollWheelZoom: false }).setView([52.5, -1.5], 6);
      mapInstance.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 18,
      }).addTo(map);

      const bounds: [number, number][] = [];

      validProviders.forEach((p) => {
        const lat = Number(p.latitude);
        const lon = Number(p.longitude);
        bounds.push([lat, lon]);

        const marker = L.circleMarker([lat, lon], {
          radius: 6,
          fillColor: "#C1784F",
          color: "#6B4C35",
          weight: 1,
          fillOpacity: 0.8,
        }).addTo(map);

        marker.bindPopup(
          `<strong><a href="/provider/${p.slug}" style="color:#C1784F">${p.name}</a></strong><br/>` +
          `${p.town || ""}<br/>` +
          `<span style="color:#4A5E45">${p.overall_rating}</span>`
        );
      });

      if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [20, 20] });
      } else if (bounds.length === 1) {
        map.setView(bounds[0], 14);
      }
    };

    loadMap();

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [providers]);

  return (
    <div
      ref={mapRef}
      className="w-full h-96 rounded-lg border border-stone bg-cream"
      role="img"
      aria-label="Map showing provider locations"
    />
  );
}
