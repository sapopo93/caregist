"use client";

import { useRef, useState } from "react";

import { trackEvent } from "@/lib/analytics";
import { DEFAULT_SERVICE_TYPE_OPTIONS } from "@/lib/directory-constants";
import {
  TERRITORY_BRIEF_PRICE_GBP,
  TERRITORY_BUYER_TYPES,
  TERRITORY_REGION_OPTIONS,
  type TerritoryCoverageResult,
} from "@/lib/territory-scope";

import styles from "@/app/pricing/territory/territory.module.css";

interface CoverageResponse {
  scope: { region: string; buyerType: string; serviceType: string };
  coverage: TerritoryCoverageResult;
  price: { currency: string; amount: number };
}

const VERDICT_STYLES: Record<string, string> = {
  ready: styles.resultVerdictReady,
  partial: styles.resultVerdictPartial,
  insufficient: styles.resultVerdictInsufficient,
};

export default function TerritoryScopePicker() {
  const [region, setRegion] = useState("");
  const [buyerType, setBuyerType] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CoverageResponse | null>(null);

  const requestVersion = useRef(0);

  function changeSelection(setValue: (value: string) => void, value: string) {
    requestVersion.current += 1;
    setValue(value);
    setResult(null);
    setError("");
    setLoading(false);
  }

  const selectedBuyer = TERRITORY_BUYER_TYPES.find((b) => b.value === buyerType) ?? null;
  const canCheck = Boolean(region && buyerType) && !loading;

  async function checkCoverage() {
    const version = ++requestVersion.current;
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
      if (version !== requestVersion.current) return;
      if (!res.ok) {
        setError(data.error || "Could not check that scope. Try again.");
        return;
      }
      setResult(data as CoverageResponse);
    } catch {
      if (version === requestVersion.current) setError("The coverage check failed. Try again. No order has been placed.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
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
          "Please review availability for this Territory Opportunity Brief scope. This is an enquiry, not an order.",
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
    <div className={styles.checkCard}>
      <h3>Choose your territory</h3>
      <p className={styles.checkLead}>
        Pick a region and the organisations you sell to. We check the published CQC record for
        matching organisations. This check is free and does not place an order.
      </p>

      <div className={styles.fieldGrid}>
        <div className={styles.field}>
          <label htmlFor="territory-region" className={styles.label}>
            Region
          </label>
          <select
            id="territory-region"
            value={region}
            onChange={(e) => changeSelection(setRegion, e.target.value)}
            className={styles.select}
          >
            <option value="">Choose a region…</option>
            {TERRITORY_REGION_OPTIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label htmlFor="territory-buyer" className={styles.label}>
            Which organisations do you sell to?
          </label>
          <select
            id="territory-buyer"
            value={buyerType}
            onChange={(e) => changeSelection(setBuyerType, e.target.value)}
            className={styles.select}
          >
            <option value="">Choose a buyer type…</option>
            {TERRITORY_BUYER_TYPES.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        <div className={`${styles.field} ${styles.fieldFull}`}>
          <label htmlFor="territory-service" className={styles.label}>
            Narrow to one service type <span className={styles.labelHint}>(optional)</span>
          </label>
          <select
            id="territory-service"
            value={serviceType}
            onChange={(e) => changeSelection(setServiceType, e.target.value)}
            className={styles.select}
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
        <p className={styles.buyerNote}>
          <strong>{selectedBuyer.description}.</strong> Built for{" "}
          {selectedBuyer.persona.toLowerCase()}.
        </p>
      )}

      <button
        type="button"
        onClick={() => void checkCoverage()}
        disabled={!canCheck}
        className={`${styles.button} ${styles.checkButton}`}
      >
        {loading ? "Checking the record…" : "Check this territory"}
      </button>

      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}

      {result && (
        <div className={styles.result}>
          <div
            role="status"
            aria-live="polite"
            className={`${styles.resultVerdict} ${VERDICT_STYLES[result.coverage.verdict] ?? ""}`}
          >
            <p className={styles.scopeSummary}>{scopeSummary}</p>
            <p className={styles.resultDetail}>
              {result.coverage.providerCount < 12
                ? "Too few matching organisations for the proposed brief. Try another region or remove the service filter."
                : result.coverage.providerCount < 25
                  ? "This scope has fewer than 25 matching organisations. A review is needed to establish whether a smaller brief is suitable."
                  : "This count is a starting point for reviewing your scope. It does not verify a ranked shortlist or confirm delivery availability."}
            </p>
            <dl className={styles.dl}>
              <div>
                <dt>Providers in scope</dt>
                <dd>{result.coverage.providerCount}</dd>
              </div>
              <div>
                <dt>Most recent observation</dt>
                <dd>{result.coverage.mostRecentObservation ?? "Not recorded"}</dd>
              </div>
            </dl>

            {result.coverage.canCheckout ? (
              <div style={{ marginTop: 18 }}>
                <a
                  href={mailtoHref}
                  className={styles.button}
                  onClick={() =>
                    void trackEvent("territory_scope_request", "territory_picker", {
                      region: result.scope.region,
                      buyer_type: result.scope.buyerType,
                      verdict: result.coverage.verdict,
                    })
                  }
                >
                  Email this scope for review
                </a>
                <p className={styles.note}>
                  Opens your email app with your selections. Send the email to request a
                  review. This does not reserve a brief or take payment. Online ordering is
                  not available.
                </p>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
