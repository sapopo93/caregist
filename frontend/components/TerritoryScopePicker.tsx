"use client";

import { useState } from "react";
import Link from "next/link";

import { trackEvent } from "@/lib/analytics";
import { DEFAULT_SERVICE_TYPE_OPTIONS } from "@/lib/directory-constants";
import {
  TERRITORY_BRIEF_PRICE_GBP,
  TERRITORY_BUYER_TYPES,
  TERRITORY_REGION_OPTIONS,
  type TerritoryCoverageResult,
} from "@/lib/territory-scope";

interface CoverageResponse {
  scope: { region: string; buyerType: string; serviceType: string };
  coverage: TerritoryCoverageResult;
  price: { currency: string; amount: number };
}

const VERDICT_STYLES: Record<string, string> = {
  ready: "border-moss/40 bg-moss/10",
  partial: "border-amber/40 bg-amber/10",
  insufficient: "border-clay/40 bg-clay/10",
};

export default function TerritoryScopePicker({
  checkoutEnabled,
}: {
  checkoutEnabled: boolean;
}) {
  const [region, setRegion] = useState("");
  const [buyerType, setBuyerType] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CoverageResponse | null>(null);

  const selectedBuyer = TERRITORY_BUYER_TYPES.find((b) => b.value === buyerType) ?? null;
  const canCheck = Boolean(region && buyerType) && !loading;

  async function checkCoverage() {
    setLoading(true);
    setError("");
    setResult(null);
    void trackEvent("territory_scope_check", "territory_picker", { region, buyer_type: buyerType, service_type: serviceType });
    try {
      const res = await fetch("/api/territory/coverage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ region, buyerType, serviceType }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Could not check that scope. Try again.");
        return;
      }
      setResult(data as CoverageResponse);
    } catch {
      setError("Something went wrong. No payment has been taken. Try again.");
    } finally {
      setLoading(false);
    }
  }

  const scopeSummary = result
    ? `${result.scope.region} · ${selectedBuyer?.label ?? result.scope.buyerType}${
        result.scope.serviceType ? ` · ${result.scope.serviceType}` : ""
      }`
    : "";

  const mailtoHref = result
    ? `mailto:outreach@caregist.co.uk?subject=${encodeURIComponent(
        `Territory Opportunity Brief — ${scopeSummary}`,
      )}&body=${encodeURIComponent(
        [
          "I have confirmed this scope on the pricing page and would like to buy the Territory Opportunity Brief.",
          "",
          `Region: ${result.scope.region}`,
          `Buyer type: ${selectedBuyer?.label ?? result.scope.buyerType}`,
          `Service type: ${result.scope.serviceType || "All"}`,
          `Providers in scope: ${result.coverage.providerCount}`,
          `Coverage verdict: ${result.coverage.verdict}`,
          `Price: £${TERRITORY_BRIEF_PRICE_GBP}`,
        ].join("\n"),
      )}`
    : "";

  return (
    <div className="rounded-xl border border-stone bg-cream p-6">
      <h2 className="mb-1 text-xl font-bold text-bark">Confirm your territory</h2>
      <p className="mb-5 text-sm text-dusk">
        Pick a region and the organisations you sell to. We check the published CQC
        record for that exact scope before any payment — no scoping call needed.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="territory-region" className="mb-1 block text-sm font-semibold text-bark">
            Region
          </label>
          <select
            id="territory-region"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="w-full rounded-lg border border-stone bg-cream px-3 py-2 text-sm text-charcoal"
          >
            <option value="">Choose a region…</option>
            {TERRITORY_REGION_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="territory-buyer" className="mb-1 block text-sm font-semibold text-bark">
            Which organisations do you sell to?
          </label>
          <select
            id="territory-buyer"
            value={buyerType}
            onChange={(e) => setBuyerType(e.target.value)}
            className="w-full rounded-lg border border-stone bg-cream px-3 py-2 text-sm text-charcoal"
          >
            <option value="">Choose a buyer type…</option>
            {TERRITORY_BUYER_TYPES.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2">
          <label htmlFor="territory-service" className="mb-1 block text-sm font-semibold text-bark">
            Narrow to one service type <span className="font-normal text-dusk">(optional)</span>
          </label>
          <select
            id="territory-service"
            value={serviceType}
            onChange={(e) => setServiceType(e.target.value)}
            className="w-full rounded-lg border border-stone bg-cream px-3 py-2 text-sm text-charcoal"
          >
            <option value="">All service types</option>
            {DEFAULT_SERVICE_TYPE_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {selectedBuyer && (
        <p className="mt-3 text-xs text-dusk">
          <span className="font-semibold text-bark">{selectedBuyer.description}.</span>{" "}
          Built for {selectedBuyer.persona.toLowerCase()}.
        </p>
      )}

      <button
        type="button"
        onClick={() => void checkCoverage()}
        disabled={!canCheck}
        className="mt-5 inline-block rounded-lg border border-clay px-6 py-2.5 text-sm font-medium text-clay transition-colors hover:bg-clay hover:text-white disabled:opacity-50"
      >
        {loading ? "Checking the record…" : "Check this territory"}
      </button>

      {error && <p className="mt-3 text-sm text-alert">{error}</p>}

      {result && (
        <div className={`mt-6 rounded-lg border p-4 ${VERDICT_STYLES[result.coverage.verdict] ?? "border-stone"}`}>
          <p className="text-sm font-bold text-bark">{result.coverage.headline}</p>
          <p className="mt-1 text-sm text-charcoal">{result.coverage.detail}</p>
          <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-dusk">
            <div>
              <dt className="font-semibold text-bark">Providers in scope</dt>
              <dd>{result.coverage.providerCount}</dd>
            </div>
            <div>
              <dt className="font-semibold text-bark">Most recent observation</dt>
              <dd>{result.coverage.mostRecentObservation ?? "Not recorded"}</dd>
            </div>
          </dl>

          {result.coverage.canCheckout ? (
            <div className="mt-4">
              {checkoutEnabled ? (
                <Link
                  href={`/signup?plan=territory-opportunity-brief&region=${encodeURIComponent(
                    result.scope.region,
                  )}&buyer=${encodeURIComponent(result.scope.buyerType)}`}
                  className="inline-block rounded-lg bg-clay px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-bark"
                  onClick={() =>
                    void trackEvent("territory_checkout_start", "territory_picker", {
                      region: result.scope.region,
                      buyer_type: result.scope.buyerType,
                      verdict: result.coverage.verdict,
                    })
                  }
                >
                  Continue to payment · £{TERRITORY_BRIEF_PRICE_GBP}
                </Link>
              ) : (
                <>
                  <a
                    href={mailtoHref}
                    className="inline-block rounded-lg bg-clay px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-bark"
                    onClick={() =>
                      void trackEvent("territory_scope_request", "territory_picker", {
                        region: result.scope.region,
                        buyer_type: result.scope.buyerType,
                        verdict: result.coverage.verdict,
                      })
                    }
                  >
                    Request this scope · £{TERRITORY_BRIEF_PRICE_GBP}
                  </a>
                  <p className="mt-2 text-xs text-dusk">
                    Scope is confirmed. We send a Payment Link for this exact territory,
                    then the pack follows.
                  </p>
                </>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
