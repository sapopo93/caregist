"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { DEFAULT_REGION_OPTIONS } from "@/lib/directory-constants";

interface Item {
  id: string;
  label: string;
  hint: string;
  href: string;
  group: "Search" | "Pages" | "Regions" | "Territory check";
}

const PAGES: Omit<Item, "id" | "group">[] = [
  { label: "Search the free directory", hint: "Providers by name, town or postcode", href: "/search" },
  { label: "Find care near a postcode", hint: "Radius search", href: "/find-care" },
  { label: "Pricing and products", hint: "Weekly Digest, Territory Brief", href: "/pricing" },
  { label: "Check your territory", hint: "Free coverage check", href: "/pricing/territory" },
  { label: "Data status", hint: "Source dates and coverage", href: "/data-status" },
  { label: "Why CareGist", hint: "What we claim and what we refuse to", href: "/why-caregist" },
  { label: "Compare providers", hint: "Side by side", href: "/compare" },
  { label: "Log in", hint: "Your account", href: "/login" },
];

function buildItems(query: string): Item[] {
  const q = query.trim().toLowerCase();
  const all: Item[] = [
    ...PAGES.map((p, i) => ({ ...p, id: `p${i}`, group: "Pages" as const })),
    ...DEFAULT_REGION_OPTIONS.map((r) => ({
      id: `r-${r}`,
      label: `${r} directory`,
      hint: "Browse providers in this region",
      href: `/search?region=${encodeURIComponent(r)}`,
      group: "Regions" as const,
    })),
    ...DEFAULT_REGION_OPTIONS.map((r) => ({
      id: `t-${r}`,
      label: `Territory check: ${r}`,
      hint: "Free coverage check",
      href: `/pricing/territory?region=${encodeURIComponent(r)}`,
      group: "Territory check" as const,
    })),
  ];
  const matched = q ? all.filter((i) => `${i.label} ${i.hint}`.toLowerCase().includes(q)) : all.slice(0, 8);
  const search: Item[] = q
    ? [{ id: "q", label: `Search providers for “${query.trim()}”`, hint: "Name, town or postcode", href: `/search?q=${encodeURIComponent(query.trim())}`, group: "Search" }]
    : [];
  return [...search, ...matched].slice(0, 12);
}

export default function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const items = useMemo(() => buildItems(query), [query]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const typing = !!target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setOpen(true);
      }
    }
    function onOpen() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("caregist:open-palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("caregist:open-palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  function go(item: Item | undefined) {
    if (!item) return;
    setOpen(false);
    router.push(item.href);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-charcoal/60 px-4 pt-[12vh] print:hidden" onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
      <div role="dialog" aria-modal="true" aria-label="Jump to" className="w-full max-w-xl overflow-hidden rounded-2xl border border-stone bg-cream shadow-2xl">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setActive(0); }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            else if (e.key === "Enter") { e.preventDefault(); go(items[active]); }
            else if (e.key === "Escape") { e.preventDefault(); setOpen(false); }
          }}
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-list"
          aria-activedescendant={items[active] ? `palette-${items[active].id}` : undefined}
          placeholder="Jump to a page or region, or search providers…"
          className="h-14 w-full border-b border-stone bg-transparent px-5 text-base text-charcoal placeholder:text-dusk focus:outline-none"
        />
        <ul id="palette-list" role="listbox" className="max-h-[50vh] overflow-y-auto p-2">
          {items.map((item, i) => (
            <li
              key={item.id}
              id={`palette-${item.id}`}
              role="option"
              aria-selected={i === active}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => { e.preventDefault(); go(item); }}
              className={`flex cursor-pointer items-center justify-between gap-4 rounded-lg px-3 py-2.5 ${i === active ? "bg-parchment" : ""}`}
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-bark">{item.label}</span>
                <span className="block truncate text-xs text-dusk">{item.hint}</span>
              </span>
              <span className="shrink-0 font-mono text-[0.65rem] uppercase tracking-wider text-clay">{item.group}</span>
            </li>
          ))}
          {items.length === 0 ? <li className="px-3 py-6 text-center text-sm text-dusk">No matches.</li> : null}
        </ul>
        <p className="border-t border-stone px-5 py-2 font-mono text-[0.65rem] uppercase tracking-wider text-dusk">
          ↑↓ move · Enter open · Esc close
        </p>
      </div>
    </div>
  );
}
