"use client";

import { useState } from "react";
import FilterSidebar from "./FilterSidebar";

export default function MobileFilterToggle() {
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden mb-4">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 bg-cream border border-stone rounded-lg text-sm text-bark font-medium"
      >
        {open ? "Hide Filters" : "Show Filters"}
      </button>
      {open && (
        <div className="mt-3">
          <FilterSidebar />
        </div>
      )}
    </div>
  );
}
