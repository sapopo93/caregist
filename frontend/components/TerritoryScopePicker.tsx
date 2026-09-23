"use client";

import { useRef, useState } from "react";

import { trackEvent } from "@/lib/analytics";
import { DEFAULT_SERVICE_TYPE_OPTIONS } from "@/lib/directory-constants";
import {
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
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [company, setCompany] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [requestReference, setRequestReference] = useState("");

  const requestVersion = useRef(0);

  function changeSelection(setValue: (value: string) => void, value: string) {
    requestVersion.current += 1;
    setValue(value);
    setResult(null);
    setError("");
    setLoading(false);
    setRequestReference("");
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

  async function requestScopeReview() {
    if (!result || requesting) return;
    setRequesting(true);
    setError("");
    try {
      const response = await fetch("/api/territory/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...result.scope,
          email: contactEmail,
          name: contactName,
          company,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Could not record the scope request. Try again.");
        return;
      }
      setRequestReference(data.reference);
      void trackEvent("territory_scope_request", "territory_picker", {
        region: result.scope.region,
        buyer_type: result.scope.buyerType,
        verdict: result.coverage.verdict,
      });
    } catch {
      setError("Could not record the scope request. No order has been placed.");
    } finally {
      setRequesting(false);
    }
  }

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
              {result.coverage.providerOrganisationCount < 12
                ? "Too few matching organisations for the proposed brief. Try another region or remove the service filter."
                : result.coverage.providerOrganisationCount < 25
                  ? "This scope has fewer than 25 matching organisations. A review is needed to establish whether a smaller brief is suitable."
                  : "This count is a starting point for reviewing your scope. It does not verify a ranked shortlist or confirm delivery availability."}
            </p>
            <dl className={styles.dl}>
              <div>
                <dt>Provider organisations</dt>
                <dd>{result.coverage.providerOrganisationCount}</dd>
              </div>
              <div>
                <dt>CQC locations</dt>
                <dd>{result.coverage.locationCount}</dd>
              </div>
              <div>
                <dt>Latest CQC registration or inspection</dt>
                <dd>{result.coverage.mostRecentObservation ?? "Not recorded"}</dd>
              </div>
            </dl>

            {result.coverage.coverageSufficient ? (
              <div style={{ marginTop: 18 }}>
                {requestReference ? (
                  <p role="status" className={styles.note}>
                    Scope request recorded: <strong>{requestReference}</strong>. We will review
                    it before any commercial step. No order has been placed and no payment has
                    been taken.
                  </p>
                ) : (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      void requestScopeReview();
                    }}
                  >
                    <div className={styles.fieldGrid}>
                      <div className={styles.field}>
                        <label htmlFor="territory-contact-name" className={styles.label}>Name</label>
                        <input id="territory-contact-name" className={styles.select} value={contactName} onChange={(event) => setContactName(event.target.value)} autoComplete="name" />
                      </div>
                      <div className={styles.field}>
                        <label htmlFor="territory-company" className={styles.label}>Company</label>
                        <input id="territory-company" className={styles.select} value={company} onChange={(event) => setCompany(event.target.value)} autoComplete="organization" />
                      </div>
                      <div className={`${styles.field} ${styles.fieldFull}`}>
                        <label htmlFor="territory-contact-email" className={styles.label}>Work email</label>
                        <input id="territory-contact-email" className={styles.select} type="email" required value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} autoComplete="email" />
                      </div>
                    </div>
                    <button type="submit" className={styles.button} disabled={requesting}>
                      {requesting ? "Recording request…" : "Request a scope review"}
                    </button>
                    <p className={styles.note}>
                      This records an enquiry for review. It does not reserve a brief, enable
                      checkout, or take payment.
                    </p>
                  </form>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
