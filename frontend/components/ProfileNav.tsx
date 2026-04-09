"use client";

import { useEffect, useState } from "react";

const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "care-provided", label: "Care Provided" },
  { id: "ratings", label: "Ratings" },
  { id: "contact-details", label: "Contact" },
  { id: "enquiry", label: "Enquire" },
  { id: "reviews", label: "Reviews" },
];

export default function ProfileNav() {
  const [active, setActive] = useState("overview");

  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    for (const section of SECTIONS) {
      const el = document.getElementById(section.id);
      if (!el) continue;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setActive(section.id);
          }
        },
        { rootMargin: "-80px 0px -60% 0px", threshold: 0 }
      );
      observer.observe(el);
      observers.push(observer);
    }

    return () => observers.forEach((o) => o.disconnect());
  }, []);

  return (
    <nav className="sticky top-0 z-30 bg-white/95 backdrop-blur-sm border-b border-stone mb-6 -mx-6 px-6 print:hidden">
      <div className="flex gap-1 overflow-x-auto no-scrollbar">
        {SECTIONS.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById(s.id)?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            className={`whitespace-nowrap px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              active === s.id
                ? "border-clay text-clay"
                : "border-transparent text-dusk hover:text-bark hover:border-stone"
            }`}
          >
            {s.label}
          </a>
        ))}
      </div>
    </nav>
  );
}
