"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type RadarEvent = {
  event_id: string;
  event_type: "new_registration" | "rating_changed";
  effective_at: string;
  observed_at: string;
  entity: {
    level: string;
    cqc_location_id: string;
    name: string;
  };
  change: { old: unknown; new: unknown };
  source: { url: string; snapshot_sha256: string | null };
  explanation: {
    status: string;
    facts: string[];
    interpretation: string[];
  };
  ranking: { reasons: string[] };
  provider: {
    region: string | null;
    local_authority: string | null;
    town: string | null;
    service_types: string | null;
  };
};

type SavedView = {
  id: string;
  name: string;
  filters: Record<string, unknown>;
};

const RADAR_TIERS = new Set(["radar-regional", "radar-national"]);

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not recorded";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function eventTitle(event: RadarEvent) {
  return event.event_type === "new_registration" ? "New registration" : "Rating changed";
}

export default function RadarPanel({ tier }: { tier: string }) {
  const hasRadar = RADAR_TIERS.has(tier);
  const [events, setEvents] = useState<RadarEvent[]>([]);
  const [views, setViews] = useState<SavedView[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [eventType, setEventType] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [viewName, setViewName] = useState("");
  const [savingView, setSavingView] = useState(false);

  const activeFilters = useMemo(() => {
    const filters: Record<string, unknown> = {};
    if (eventType) filters.event_types = [eventType];
    if (query.trim()) filters.q = query.trim();
    return filters;
  }, [eventType, query]);

  async function loadEvents(cursor?: string, append = false, filters = activeFilters) {
    if (!hasRadar) return;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ limit: "50" });
    const selectedTypes = filters.event_types;
    if (Array.isArray(selectedTypes)) {
      selectedTypes.forEach((type) => params.append("event_type", String(type)));
    }
    if (filters.q) params.set("q", String(filters.q));
    if (cursor) params.set("cursor", cursor);
    try {
      const response = await fetch(`/api/v1/radar/events?${params.toString()}`, {
        credentials: "include",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load Radar events.");
      const nextEvents = Array.isArray(data.data) ? data.data : [];
      setEvents((current) => (append ? [...current, ...nextEvents] : nextEvents));
      setNextCursor(data.meta?.next_cursor || null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not load Radar events.");
    } finally {
      setLoading(false);
    }
  }

  async function loadViews() {
    if (!hasRadar) return;
    try {
      const response = await fetch("/api/v1/radar/views", { credentials: "include" });
      const data = await response.json();
      if (response.ok) setViews(Array.isArray(data.data) ? data.data : []);
    } catch {
      // Events remain usable if saved-view retrieval is temporarily unavailable.
    }
  }

  useEffect(() => {
    if (!hasRadar) return;
    void loadEvents(undefined, false, {});
    void loadViews();
    // Initial load is tied only to the entitlement; filters are applied explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasRadar]);

  async function recordAction(eventId: string, actionType: "opened" | "saved" | "dismissed") {
    try {
      await fetch(`/api/v1/radar/events/${eventId}/actions`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_type: actionType, metadata: {} }),
      });
      if (actionType === "dismissed") {
        setEvents((current) => current.filter((event) => event.event_id !== eventId));
      }
    } catch {
      setError("The event loaded, but the action could not be recorded.");
    }
  }

  async function saveView() {
    const name = viewName.trim();
    if (!name) return;
    setSavingView(true);
    setError("");
    try {
      const response = await fetch("/api/v1/radar/views", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, filters: activeFilters }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not save this view.");
      setViews((current) => [data, ...current.filter((view) => view.id !== data.id)]);
      setViewName("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not save this view.");
    } finally {
      setSavingView(false);
    }
  }

  if (!hasRadar) {
    return (
      <section className="mb-6 rounded-xl border border-stone bg-cream p-6">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-clay">Radar</p>
        <h2 className="mb-2 text-2xl font-bold text-bark">Verified CQC changes, organized for action</h2>
        <p className="mb-4 text-sm leading-6 text-dusk">
          Radar is available on the Regional and National plans. Legacy subscriptions remain
          supported but are not sold to new customers.
        </p>
        <Link href="/pricing" className="text-sm font-semibold text-clay underline">
          Compare Radar plans
        </Link>
      </section>
    );
  }

  return (
    <section className="mb-6 rounded-xl border border-stone bg-cream p-6">
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-clay">Change Ledger</p>
          <h2 className="text-2xl font-bold text-bark">Verified CQC signals</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-dusk">
            New registrations and rating changes from the canonical event ledger. Event
            activity can be quiet while collectors remain healthy.
          </p>
        </div>
        <a
          href="/api/v1/radar/events/export.csv"
          className="text-sm font-semibold text-clay underline"
        >
          Export this event scope
        </a>
      </div>

      <div className="mb-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Provider, town, or local authority"
          className="rounded-lg border border-stone bg-white px-4 py-2 text-sm"
        />
        <select
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
          className="rounded-lg border border-stone bg-white px-4 py-2 text-sm"
        >
          <option value="">Both launch signals</option>
          <option value="new_registration">New registrations</option>
          <option value="rating_changed">Rating changes</option>
        </select>
        <button
          type="button"
          onClick={() => void loadEvents()}
          disabled={loading}
          className="rounded-lg bg-clay px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Loading…" : "Apply"}
        </button>
      </div>

      <div className="mb-6 rounded-lg border border-stone bg-parchment p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <input
            value={viewName}
            onChange={(event) => setViewName(event.target.value)}
            placeholder="Name this view"
            className="flex-1 rounded-lg border border-stone bg-white px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => void saveView()}
            disabled={savingView || !viewName.trim()}
            className="rounded-lg border border-clay px-4 py-2 text-sm font-semibold text-clay disabled:opacity-50"
          >
            {savingView ? "Saving…" : "Save current view"}
          </button>
        </div>
        {views.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {views.map((view) => (
              <button
                key={view.id}
                type="button"
                onClick={() => {
                  const types = Array.isArray(view.filters.event_types) ? view.filters.event_types : [];
                  const nextType = types.length === 1 ? String(types[0]) : "";
                  const nextQuery = typeof view.filters.q === "string" ? view.filters.q : "";
                  setEventType(nextType);
                  setQuery(nextQuery);
                  void loadEvents(undefined, false, view.filters);
                }}
                className="rounded-full border border-stone bg-white px-3 py-1 text-xs text-bark"
              >
                {view.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-alert">{error}</p>}
      {!loading && events.length === 0 && !error && (
        <p className="rounded-lg border border-stone bg-white p-5 text-sm text-dusk">
          No verified events matched this view. This does not indicate a collector outage.
        </p>
      )}

      <div className="space-y-4">
        {events.map((event) => (
          <article key={event.event_id} className="rounded-xl border border-stone bg-white p-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-clay">
                  {eventTitle(event)} · {event.entity.level}
                </p>
                <h3 className="mt-2 text-xl font-bold text-bark">{event.entity.name}</h3>
                <p className="mt-1 text-sm text-dusk">
                  {[event.provider.town, event.provider.local_authority, event.provider.region]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <p className="font-mono text-xs text-dusk">
                Effective {new Date(event.effective_at).toLocaleDateString("en-GB")}
              </p>
            </div>

            <div className="mt-4 rounded-lg bg-parchment px-4 py-3 text-sm text-bark">
              {event.event_type === "rating_changed" ? (
                <p>
                  <span className="text-dusk">From:</span> {displayValue(event.change.old)}{" "}
                  <span className="ml-3 text-dusk">To:</span> {displayValue(event.change.new)}
                </p>
              ) : (
                <p>Location ID: {event.entity.cqc_location_id}</p>
              )}
            </div>

            {event.explanation.status === "published" ? (
              <div className="mt-4 text-sm leading-6 text-charcoal">
                <p className="font-semibold text-bark">Source facts</p>
                <ul className="list-disc pl-5">
                  {event.explanation.facts.map((fact) => <li key={fact}>{fact}</li>)}
                </ul>
                {event.explanation.interpretation.length > 0 && (
                  <>
                    <p className="mt-3 font-semibold text-bark">CareGist interpretation</p>
                    <ul className="list-disc pl-5">
                      {event.explanation.interpretation.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </>
                )}
              </div>
            ) : (
              <p className="mt-4 text-xs text-dusk">
                Verified raw event. No narrative has passed the evidence-publication gate.
              </p>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-stone pt-4 text-sm">
              <a
                href={event.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-clay underline"
                onClick={() => void recordAction(event.event_id, "opened")}
              >
                Open official evidence
              </a>
              <button type="button" onClick={() => void recordAction(event.event_id, "saved")} className="text-clay underline">
                Save event
              </button>
              <button type="button" onClick={() => void recordAction(event.event_id, "dismissed")} className="text-dusk underline">
                Dismiss
              </button>
              <span className="ml-auto font-mono text-[10px] text-dusk">
                {event.source.snapshot_sha256 ? `Snapshot ${event.source.snapshot_sha256.slice(0, 12)}…` : "Snapshot pending"}
              </span>
            </div>
          </article>
        ))}
      </div>

      {nextCursor && (
        <button
          type="button"
          onClick={() => void loadEvents(nextCursor, true)}
          disabled={loading}
          className="mt-5 rounded-lg border border-stone px-4 py-2 text-sm text-bark disabled:opacity-50"
        >
          Load older events
        </button>
      )}
    </section>
  );
}
