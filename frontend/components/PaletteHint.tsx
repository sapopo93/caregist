"use client";

import { useEffect, useState } from "react";

/** Small keyboard hint inside the header search box; opens the command palette on click. */
export default function PaletteHint() {
  const [mac, setMac] = useState(false);
  useEffect(() => setMac(/Mac|iPhone|iPad/.test(navigator.platform)), []);
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("caregist:open-palette"))}
      aria-label="Open quick jump menu"
      className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md border border-cream/30 px-1.5 py-0.5 font-mono text-[0.65rem] text-cream/80 transition hover:border-amber hover:text-amber"
    >
      {mac ? "⌘K" : "Ctrl K"}
    </button>
  );
}
