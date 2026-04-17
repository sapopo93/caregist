"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { trackEvent } from "@/lib/analytics";

type FeedFilters = {
  q: string;
  region: string;
  local_authority: string;
  service_type: string;
  provider_type: string;
  postcode_prefix: string;
  from_date: string;
  to_date: string;
};

type FeedEvent = {
  id?: number;
  effective_date: string;
  confidence_score: number;
  name: string;
  slug: string;
  service_types?: string;
  type?: string;
  region?: string;
  local_authority?: string;
  town?: string;
  postcode?: string;
};

const EMPTY_FILTERS: FeedFilters = {
  q: "",
  region: "",
  local_authority: "",
  service_type: "",
  provider_type: "",
  postcode_prefix: "",
  from_date: "",
  to_date: "",
};

function buildFeedQuery(filters: FeedFilters, page = 1) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  params.set("page", String(page));
  return params.toString();
}

export default function NewRegistrationFeedPanel({
  tier,
  upgradeHref,
}: {
  tier: string;
  upgradeHref: string;
}) {
  const [filters, setFilters] = useState<FeedFilters>(EMPTY_FILTERS);
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [savedFilters, setSavedFilters] = useState<any[]>([]);
  const [savedFilterName, setSavedFilterName] = useState("");
  const [savedFilterError, setSavedFilterError] = useState("");
  const [saveLoading, setSaveLoading] = useState(false);
  const [digest, setDigest] = useState<any>(null);
  const [digestLoading, setDigestLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState<"" | "csv" | "xlsx">("");

  async function loadFeed(nextPage = page, nextFilters = filters) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/v1/feed/new-registrations?${buildFeedQuery(nextFilters, nextPage)}`, {
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Could not load the new registration feed.");
        setEvents([]);
        setMeta(null);
        return;
      }
      setEvents(Array.isArray(data?.data) ? data.data : []);
      setMeta(data?.meta || null);
      setPage(nextPage);
    } catch {
      setError("Could not load the new registration feed.");
      setEvents([]);
      setMeta(null);
    } finally {
      setLoading(false);
    }
  }

  async function loadSavedFilters() {
    try {
      const res = await fetch("/api/v1/feed/new-registrations/saved-filters", {
        credentials: "include",
      });
      if (res.status === 403) {
        setSavedFilters([]);
        return;
      }
      const data = await res.json();
      setSavedFilters(Array.isArray(data?.filters) ? data.filters : []);
    } catch {
      setSavedFilters([]);
    }
  }

  async function loadDigest() {
    try {
      const res = await fetch("/api/v1/feed/new-registrations/digest", {
        credentials: "include",
      });
      if (res.status === 403) {
        setDigest(null);
        return;
      }
      const data = await res.json();
      setDigest(data?.subscription || null);
    } catch {
      setDigest(null);
    }
  }

  useEffect(() => {
    void loadFeed(1, EMPTY_FILTERS);
    void loadSavedFilters();
    void loadDigest();
  }, []);

  async function handleExport(format: "csv" | "xlsx") {
    setExportLoading(format);
    setError("");
    try {
      const res = await fetch(`/api/v1/feed/new-registrations/export.${format}?${buildFeedQuery(filters, 1)}`, {
        credentials: "include",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || `Could not export ${format.toUpperCase()}.`);
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = format === "csv" ? "new-registrations.csv" : "new-registrations.xlsx";
      anchor.click();
      window.URL.revokeObjectURL(url);
      void trackEvent("new_registration_feed_export", "dashboard_feed_panel", { tier, format });
    } catch {
      setError(`Could not export ${format.toUpperCase()}.`);
    } finally {
      setExportLoading("");
    }
  }

  async function handleSaveFilter() {
    if (!savedFilterName.trim()) return;
    setSaveLoading(true);
    setSavedFilterError("");
    try {
      const res = await fetch("/api/v1/feed/new-registrations/saved-filters", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: savedFilterName.trim(), filters }),
      });
      const data = await res.json();
      if (!res.ok) {
        setSavedFilterError(data.detail || "Could not save this feed view.");
        return;
      }
      setSavedFilterName("");
      setSavedFilters((current) => [data, ...current.filter((item) => item.id !== data.id)]);
      void trackEvent("new_registration_feed_filter_saved", "dashboard_feed_panel", { tier });
    } catch {
      setSavedFilterError("Could not save this feed view.");
    } finally {
      setSaveLoading(false);
    }
  }

  async function handleDeleteSavedFilter(filterId: number) {
    await fetch(`/api/v1/feed/new-registrations/saved-filters/${filterId}`, {
      method: "DELETE",
      credentials: "include",
    });
    setSavedFilters((current) => current.filter((item) => item.id !== filterId));
  }

  async function handleDigestToggle(active: boolean) {
    setDigestLoading(true);
    try {
      const res = await fetch("/api/v1/feed/new-registrations/digest", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active, filters }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Could not update weekly digest settings.");
        return;
      }
      setDigest(data?.subscription || null);
      void trackEvent("new_registration_feed_digest_updated", "dashboard_feed_panel", { tier, active });
    } catch {
      setError("Could not update weekly digest settings.");
    } finally {
      setDigestLoading(false);
    }
  }

  const nextPage = meta?.page && meta?.pages && meta.page < meta.pages ? meta.page + 1 : null;
  const previousPage = meta?.page && meta.page > 1 ? meta.page - 1 : null;
  const hasSavedFilterAccess = tier !== "free";
  const hasDigestAccess = tier !== "free";
  const canExport = tier !== "free";
  const supportsWebhooks = tier === "business" || tier === "enterprise";

  return (
    <section className="bg-cream border border-stone rounded-lg p-6 mb-6">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-clay mb-2">Launch wedge</p>
          <h2 className="text-2xl font-bold mb-2">New registration feed</h2>
          <p className="text-dusk text-sm max-w-3xl">
            Newly registered UK care providers, delivered as a filtered recurring intelligence feed. The feed runs off the trusted event ledger, so exports, digests, API access, and webhooks all read from the same source of truth.
          </p>
        </div>
        <div className="rounded-lg bg-parchment border border-stone px-4 py-3 min-w-[16rem]">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-dusk mb-1">Plan fit</p>
          <p className="text-sm text-bark">
            {tier === "free"
              ? "Free is evaluation only. Starter is the first paid tier for recurring feed workflows."
              : tier === "starter"
                ? "Starter gets the first real recurring feed workflow: filtering, exports, saved views, and one digest."
                : tier === "pro"
                  ? "Pro is the recommended small-team production tier for recurring feed use."
                  : "Business adds programmatic delivery through webhooks and broader operational headroom."}
          </p>
        </div>
      </div>

      <div className="grid xl:grid-cols-[1.8fr_1fr] gap-6">
        <div>
          <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
            <input value={filters.q} onChange={(e) => setFilters((current) => ({ ...current, q: e.target.value }))} placeholder="Search provider or town" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.region} onChange={(e) => setFilters((current) => ({ ...current, region: e.target.value }))} placeholder="Region" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.local_authority} onChange={(e) => setFilters((current) => ({ ...current, local_authority: e.target.value }))} placeholder="Local authority" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.service_type} onChange={(e) => setFilters((current) => ({ ...current, service_type: e.target.value }))} placeholder="Service type" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.provider_type} onChange={(e) => setFilters((current) => ({ ...current, provider_type: e.target.value }))} placeholder="Provider type" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.postcode_prefix} onChange={(e) => setFilters((current) => ({ ...current, postcode_prefix: e.target.value }))} placeholder="Postcode prefix" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.from_date} onChange={(e) => setFilters((current) => ({ ...current, from_date: e.target.value }))} type="date" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
            <input value={filters.to_date} onChange={(e) => setFilters((current) => ({ ...current, to_date: e.target.value }))} type="date" className="px-3 py-2 rounded border border-stone bg-white text-sm" />
          </div>

          <div className="flex flex-wrap gap-3 mb-4">
            <button onClick={() => void loadFeed(1, filters)} disabled={loading} className="px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors disabled:opacity-50">
              {loading ? "Loading..." : "Apply filters"}
            </button>
            <button
              onClick={() => {
                setFilters(EMPTY_FILTERS);
                void loadFeed(1, EMPTY_FILTERS);
              }}
              className="px-4 py-2 border border-stone rounded-lg text-sm text-bark hover:bg-parchment transition-colors"
            >
              Reset
            </button>
            <button onClick={() => void handleExport("csv")} disabled={!canExport || exportLoading !== ""} className="px-4 py-2 border border-stone rounded-lg text-sm text-bark hover:bg-parchment transition-colors disabled:opacity-50">
              {exportLoading === "csv" ? "Exporting..." : "Export CSV"}
            </button>
            <button onClick={() => void handleExport("xlsx")} disabled={!canExport || exportLoading !== ""} className="px-4 py-2 border border-stone rounded-lg text-sm text-bark hover:bg-parchment transition-colors disabled:opacity-50">
              {exportLoading === "xlsx" ? "Exporting..." : "Export Excel"}
            </button>
          </div>

          <div className="rounded-lg bg-parchment border border-stone px-4 py-3 mb-4 text-sm text-dusk">
            {meta ? (
              <span>
                Showing {events.length} of {meta.total} matching new-registration events on the {meta.tier} tier.
              </span>
            ) : (
              <span>Load the latest new-registration events to start the workflow.</span>
            )}
            {!canExport && (
              <span className="block mt-1">
                Free is evaluation only. Starter unlocks recurring exports, saved views, and weekly digest delivery.
              </span>
            )}
          </div>

          {error && <p className="text-sm text-alert mb-4">{error}</p>}

          <div className="overflow-x-auto border border-stone rounded-lg bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-parchment text-bark">
                <tr>
                  <th className="text-left px-4 py-3">Provider</th>
                  <th className="text-left px-4 py-3">Service type</th>
                  <th className="text-left px-4 py-3">Authority</th>
                  <th className="text-left px-4 py-3">Region</th>
                  <th className="text-left px-4 py-3">Registered</th>
                  <th className="text-left px-4 py-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {events.length === 0 && !loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-dusk">
                      No new registrations matched this filter.
                    </td>
                  </tr>
                ) : (
                  events.map((event) => (
                    <tr key={`${event.slug}-${event.effective_date}`} className="border-t border-stone">
                      <td className="px-4 py-3">
                        <Link href={`/provider/${event.slug}`} className="font-medium text-bark underline-offset-4 hover:underline">
                          {event.name}
                        </Link>
                        <div className="text-xs text-dusk mt-1">{event.town || "Unknown town"} · {event.postcode || "No postcode"}</div>
                      </td>
                      <td className="px-4 py-3 text-dusk">{event.service_types || "—"}</td>
                      <td className="px-4 py-3 text-dusk">{event.local_authority || "—"}</td>
                      <td className="px-4 py-3 text-dusk">{event.region || "—"}</td>
                      <td className="px-4 py-3 text-dusk">{event.effective_date}</td>
                      <td className="px-4 py-3 text-dusk">{Number(event.confidence_score || 0).toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-sm">
            <div className="text-dusk">
              {supportsWebhooks
                ? "Business webhooks can deliver feed.new_registration payloads from this same ledger."
                : "Business adds webhook delivery of feed.new_registration for downstream CRM or ops systems."}
            </div>
            <div className="flex gap-3">
              <button onClick={() => previousPage && void loadFeed(previousPage, filters)} disabled={!previousPage || loading} className="px-3 py-2 border border-stone rounded-lg disabled:opacity-50">
                Previous
              </button>
              <button onClick={() => nextPage && void loadFeed(nextPage, filters)} disabled={!nextPage || loading} className="px-3 py-2 border border-stone rounded-lg disabled:opacity-50">
                Next
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-stone bg-parchment p-4">
            <h3 className="text-lg font-bold text-bark mb-2">Saved views</h3>
            <p className="text-xs text-dusk mb-3">
              Save recurring feed filters once the view matches your commercial patch.
            </p>
            {hasSavedFilterAccess ? (
              <>
                <input value={savedFilterName} onChange={(e) => setSavedFilterName(e.target.value)} placeholder="e.g. London home care openings" className="w-full px-3 py-2 rounded border border-stone bg-white text-sm mb-3" />
                <button onClick={() => void handleSaveFilter()} disabled={saveLoading} className="w-full px-4 py-2 bg-clay text-white rounded-lg text-sm hover:bg-bark transition-colors disabled:opacity-50">
                  {saveLoading ? "Saving..." : "Save current filter"}
                </button>
                {savedFilterError && <p className="text-xs text-alert mt-2">{savedFilterError}</p>}
                <div className="mt-4 space-y-3">
                  {savedFilters.length === 0 ? (
                    <p className="text-xs text-dusk">No saved views yet.</p>
                  ) : (
                    savedFilters.map((item) => (
                      <div key={item.id} className="border border-stone rounded-lg bg-white p-3">
                        <p className="font-medium text-bark text-sm">{item.name}</p>
                        <div className="flex gap-3 mt-2 text-xs">
                          <button
                            onClick={() => {
                              const nextFilters = { ...EMPTY_FILTERS, ...item.filters };
                              setFilters(nextFilters);
                              void loadFeed(1, nextFilters);
                            }}
                            className="text-clay underline"
                          >
                            Open
                          </button>
                          <button onClick={() => void handleDeleteSavedFilter(item.id)} className="text-dusk underline">
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-dusk">
                Saved feed views start on Starter.{" "}
                <Link href={upgradeHref} className="text-clay underline">Upgrade</Link>
              </p>
            )}
          </div>

          <div className="rounded-lg border border-stone bg-parchment p-4">
            <h3 className="text-lg font-bold text-bark mb-2">Weekly digest</h3>
            <p className="text-xs text-dusk mb-3">
              Queue a weekly digest off the same filter logic so the workflow stays low-touch.
            </p>
            {hasDigestAccess ? (
              <>
                <button
                  onClick={() => void handleDigestToggle(!(digest?.active ?? false))}
                  disabled={digestLoading}
                  className="w-full px-4 py-2 bg-bark text-white rounded-lg text-sm hover:bg-charcoal transition-colors disabled:opacity-50"
                >
                  {digestLoading ? "Updating..." : digest?.active ? "Pause weekly digest" : "Enable weekly digest"}
                </button>
                <p className="text-xs text-dusk mt-3">
                  {digest?.active
                    ? "Weekly digest is active for the current user and can be paused any time."
                    : "Digest is not active yet. Enable it to queue a weekly view of newly registered providers."}
                </p>
              </>
            ) : (
              <p className="text-sm text-dusk">
                Weekly digests start on Starter.{" "}
                <Link href={upgradeHref} className="text-clay underline">Upgrade</Link>
              </p>
            )}
          </div>

          <div className="rounded-lg border border-stone bg-parchment p-4">
            <h3 className="text-lg font-bold text-bark mb-2">Programmatic delivery</h3>
            <p className="text-xs text-dusk mb-3">
              Higher tiers can move this wedge from dashboard use into recurring operational delivery.
            </p>
            <ul className="space-y-2 text-xs text-dusk">
              <li>Starter: filtered feed view, exports, saved views, one weekly digest.</li>
              <li>Pro: recommended for small-team production and wider recurring usage.</li>
              <li>Business: signed webhooks for <code className="bg-white px-1 rounded">feed.new_registration</code>.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
