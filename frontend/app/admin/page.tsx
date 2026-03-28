"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "/api";

type Tab = "stats" | "claims" | "reviews" | "enquiries";

export default function AdminPage() {
  const [apiKey, setApiKey] = useState("");
  const [authed, setAuthed] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("stats");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const adminFetch = useCallback(async (path: string, options?: RequestInit) => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "X-API-Key": apiKey, "Content-Type": "application/json", ...options?.headers },
    });
    if (res.status === 403) { setAuthed(false); setError("Admin access denied."); return null; }
    if (!res.ok) { setError(`Request failed: ${res.status}`); return null; }
    return res.json();
  }, [apiKey]);

  const loadTab = useCallback(async () => {
    setLoading(true);
    setError("");
    let result;
    if (tab === "stats") result = await adminFetch("/v1/admin/stats");
    else if (tab === "claims") result = await adminFetch("/v1/admin/claims?status=pending");
    else if (tab === "reviews") result = await adminFetch("/v1/admin/reviews?status=pending");
    else if (tab === "enquiries") result = await adminFetch("/v1/admin/enquiries?status=new");
    setData(result);
    setLoading(false);
  }, [tab, adminFetch]);

  useEffect(() => { if (authed) loadTab(); }, [authed, tab, loadTab]);

  async function handleAuth(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch(`${API_BASE}/v1/admin/stats`, {
      headers: { "X-API-Key": apiKey },
    });
    if (res.ok) { setAuthed(true); }
    else { setError("Invalid admin key."); }
  }

  async function moderateClaim(id: number, status: "approved" | "rejected") {
    await adminFetch(`/v1/admin/claims/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadTab();
  }

  async function moderateReview(id: number, status: "approved" | "rejected") {
    await adminFetch(`/v1/admin/reviews/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadTab();
  }

  async function updateEnquiry(id: number, status: "read" | "responded") {
    await adminFetch(`/v1/admin/enquiries/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    loadTab();
  }

  if (!authed) {
    return (
      <div className="max-w-md mx-auto px-6 py-12">
        <h1 className="text-2xl font-bold text-bark mb-6">Admin Dashboard</h1>
        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label htmlFor="admin-key" className="block text-sm font-medium text-bark mb-1">Master API Key</label>
            <input id="admin-key" type="password" required value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              className="w-full border border-stone rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-clay/50" />
          </div>
          {error && <p className="text-alert text-sm">{error}</p>}
          <button type="submit" className="w-full px-6 py-2.5 bg-bark text-cream rounded-lg font-medium hover:bg-charcoal transition-colors">
            Sign In
          </button>
        </form>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "stats", label: "Dashboard" },
    { key: "claims", label: "Claims" },
    { key: "reviews", label: "Reviews" },
    { key: "enquiries", label: "Enquiries" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-bark mb-6">Admin Dashboard</h1>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-stone mb-6">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors -mb-px ${
              tab === t.key ? "border-b-2 border-clay text-clay" : "text-dusk hover:text-bark"
            }`}>
            {t.label}
            {data && tab !== t.key && t.key === "claims" && data?.meta?.total > 0 && (
              <span className="ml-1 bg-alert text-white text-xs px-1.5 py-0.5 rounded-full">{data.meta.total}</span>
            )}
          </button>
        ))}
      </div>

      {error && <p className="text-alert text-sm mb-4">{error}</p>}
      {loading && <p className="text-dusk">Loading...</p>}

      {/* Stats tab */}
      {tab === "stats" && data?.data && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Providers" value={data.data.total_providers} />
            <StatCard label="Claimed" value={data.data.claimed_providers} accent />
            <StatCard label="Pending Claims" value={data.data.pending_claims} alert={data.data.pending_claims > 0} />
            <StatCard label="Pending Reviews" value={data.data.pending_reviews} alert={data.data.pending_reviews > 0} />
            <StatCard label="New Enquiries" value={data.data.new_enquiries} alert={data.data.new_enquiries > 0} />
            <StatCard label="Total Reviews" value={data.data.total_reviews} />
            <StatCard label="Total Enquiries" value={data.data.total_enquiries} accent />
          </div>

          {data.top_enquired?.length > 0 && (
            <div>
              <h2 className="text-lg font-bold mb-3">Top Enquired Providers</h2>
              <div className="border border-stone rounded-lg overflow-hidden">
                {data.top_enquired.map((p: any, i: number) => (
                  <div key={p.slug} className={`flex items-center justify-between px-4 py-3 ${i % 2 ? "bg-parchment/50" : ""} ${i > 0 ? "border-t border-stone" : ""}`}>
                    <div>
                      <span className="font-medium text-bark">{p.name}</span>
                      {p.is_claimed && <span className="ml-2 text-xs text-moss">Verified</span>}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-dusk">
                      <span>{p.enquiry_count} enquiries</span>
                      <span className="text-xs bg-parchment px-2 py-0.5 rounded">{p.overall_rating || "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Claims tab */}
      {tab === "claims" && data?.data && (
        <div className="space-y-4">
          {data.data.length === 0 && <p className="text-dusk">No pending claims.</p>}
          {data.data.map((claim: any) => (
            <div key={claim.id} className="border border-stone rounded-lg p-4 bg-cream">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="font-semibold text-bark">{claim.provider_name}</span>
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                    claim.status === "pending" ? "bg-amber/20 text-amber" : claim.status === "approved" ? "bg-moss/20 text-moss" : "bg-alert/20 text-alert"
                  }`}>{claim.status}</span>
                </div>
                <span className="text-xs text-dusk">{new Date(claim.created_at).toLocaleDateString("en-GB")}</span>
              </div>
              <div className="grid md:grid-cols-2 gap-2 text-sm mb-3">
                <p><span className="text-dusk">Name:</span> {claim.claimant_name}</p>
                <p><span className="text-dusk">Email:</span> {claim.claimant_email}</p>
                <p><span className="text-dusk">Role:</span> {claim.claimant_role}</p>
                {claim.claimant_phone && <p><span className="text-dusk">Phone:</span> {claim.claimant_phone}</p>}
              </div>
              {claim.proof_of_association && <p className="text-sm mb-3"><span className="text-dusk">Proof:</span> {claim.proof_of_association}</p>}
              {claim.status === "pending" && (
                <div className="flex gap-2">
                  <button onClick={() => moderateClaim(claim.id, "approved")}
                    className="px-4 py-1.5 bg-moss text-white rounded text-sm font-medium hover:bg-moss/80">Approve</button>
                  <button onClick={() => moderateClaim(claim.id, "rejected")}
                    className="px-4 py-1.5 bg-alert text-white rounded text-sm font-medium hover:bg-alert/80">Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Reviews tab */}
      {tab === "reviews" && data?.data && (
        <div className="space-y-4">
          {data.data.length === 0 && <p className="text-dusk">No pending reviews.</p>}
          {data.data.map((review: any) => (
            <div key={review.id} className="border border-stone rounded-lg p-4 bg-cream">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="font-semibold text-bark">{review.provider_name}</span>
                  <span className="ml-2 text-amber">{"*".repeat(review.rating)}</span>
                </div>
                <span className="text-xs text-dusk">{new Date(review.created_at).toLocaleDateString("en-GB")}</span>
              </div>
              <h4 className="font-medium mb-1">{review.title}</h4>
              <p className="text-sm text-charcoal mb-2">{review.body}</p>
              <p className="text-sm text-dusk mb-3">By {review.reviewer_name} ({review.reviewer_email}){review.relationship ? ` — ${review.relationship}` : ""}</p>
              {review.status === "pending" && (
                <div className="flex gap-2">
                  <button onClick={() => moderateReview(review.id, "approved")}
                    className="px-4 py-1.5 bg-moss text-white rounded text-sm font-medium hover:bg-moss/80">Approve</button>
                  <button onClick={() => moderateReview(review.id, "rejected")}
                    className="px-4 py-1.5 bg-alert text-white rounded text-sm font-medium hover:bg-alert/80">Reject</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Enquiries tab */}
      {tab === "enquiries" && data?.data && (
        <div className="space-y-4">
          {data.data.length === 0 && <p className="text-dusk">No new enquiries.</p>}
          {data.data.map((enq: any) => (
            <div key={enq.id} className="border border-stone rounded-lg p-4 bg-cream">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="font-semibold text-bark">{enq.provider_name}</span>
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                    enq.status === "new" ? "bg-clay/20 text-clay" : enq.status === "read" ? "bg-amber/20 text-amber" : "bg-moss/20 text-moss"
                  }`}>{enq.status}</span>
                </div>
                <span className="text-xs text-dusk">{new Date(enq.created_at).toLocaleDateString("en-GB")}</span>
              </div>
              <div className="grid md:grid-cols-3 gap-2 text-sm mb-2">
                <p><span className="text-dusk">From:</span> {enq.enquirer_name}</p>
                <p><span className="text-dusk">Email:</span> {enq.enquirer_email}</p>
                {enq.enquirer_phone && <p><span className="text-dusk">Phone:</span> {enq.enquirer_phone}</p>}
              </div>
              <div className="flex gap-4 text-sm text-dusk mb-2">
                {enq.relationship && <span>Relationship: {enq.relationship}</span>}
                {enq.care_type && <span>Care type: {enq.care_type}</span>}
                {enq.urgency && <span>Urgency: {enq.urgency}</span>}
              </div>
              <p className="text-sm bg-parchment rounded p-3 mb-3">{enq.message}</p>
              {enq.status === "new" && (
                <div className="flex gap-2">
                  <button onClick={() => updateEnquiry(enq.id, "read")}
                    className="px-4 py-1.5 bg-bark text-cream rounded text-sm font-medium hover:bg-charcoal">Mark Read</button>
                  <button onClick={() => updateEnquiry(enq.id, "responded")}
                    className="px-4 py-1.5 bg-moss text-white rounded text-sm font-medium hover:bg-moss/80">Mark Responded</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent = false, alert = false }: { label: string; value: number; accent?: boolean; alert?: boolean }) {
  return (
    <div className={`rounded-lg p-4 border ${alert ? "border-alert/30 bg-alert/5" : accent ? "border-clay/30 bg-clay/5" : "border-stone bg-cream"}`}>
      <div className={`text-2xl font-bold ${alert ? "text-alert" : accent ? "text-clay" : "text-bark"}`}>
        {value?.toLocaleString() ?? 0}
      </div>
      <div className="text-sm text-dusk">{label}</div>
    </div>
  );
}
