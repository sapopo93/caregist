"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "caregist_compare";
const MAX_COMPARE = 3;

function getCompareList(): { slug: string; name: string }[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function setCompareList(list: { slug: string; name: string }[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("compare-updated"));
}

export default function CompareButton({ slug, name }: { slug: string; name: string }) {
  const [isSelected, setIsSelected] = useState(false);

  useEffect(() => {
    const check = () => setIsSelected(getCompareList().some((p) => p.slug === slug));
    check();
    window.addEventListener("compare-updated", check);
    return () => window.removeEventListener("compare-updated", check);
  }, [slug]);

  function toggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    const list = getCompareList();
    if (isSelected) {
      setCompareList(list.filter((p) => p.slug !== slug));
    } else if (list.length < MAX_COMPARE) {
      setCompareList([...list, { slug, name }]);
    }
  }

  return (
    <button
      onClick={toggle}
      className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
        isSelected
          ? "bg-clay/10 border-clay text-clay"
          : "border-stone text-dusk hover:border-clay hover:text-clay"
      }`}
      aria-label={isSelected ? "Remove from comparison" : "Add to comparison"}
      title={isSelected ? "Remove from comparison" : `Compare (${getCompareList().length}/${MAX_COMPARE})`}
    >
      {isSelected ? "- Compare" : "+ Compare"}
    </button>
  );
}
