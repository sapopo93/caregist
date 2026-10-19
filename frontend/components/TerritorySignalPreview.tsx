"use client";

import { useEffect, useState } from "react";

import { trackEvent } from "@/lib/analytics";
import {
  buildPreviewPath,
  isTerritoryPreviewEnabled,
  PREVIEW_SCOPE_NOTE,
  freshnessNotice,
  previewHeadline,
  ratingNotice,
  previewWindowLabel,
  signalLabel,
  type TerritoryPreview,
} from "@/lib/territory-preview";

import styles from "@/app/pricing/territory/territory.module.css";

const ENABLED = isTerritoryPreviewEnabled(process.env.NEXT_PUBLIC_TERRITORY_PREVIEW_ENABLED);

type State =
  | { status: "idle" | "loading" | "off" }
  | { status: "error" }
  | { status: "ready"; preview: TerritoryPreview };

/**
 * Free preview of dated public signals for the checked scope. Renders nothing
 * unless both the frontend flag and the API flag are on (the API answers 404
 * while off), or when the selected service is outside the preview's coverage.
 */
export default function TerritorySignalPreview({ region, serviceType }: { region: string; serviceType: string }) {
  const [state, setState] = useState<State>({ status: "idle" });
  const path = ENABLED ? buildPreviewPath(region, serviceType) : null;

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    setState({ status: "loading" });
    fetch(path, { signal: controller.signal })
      .then(async (res) => {
        if (res.status === 404) return setState({ status: "off" });
        if (!res.ok) return setState({ status: "error" });
        const preview = (await res.json()) as TerritoryPreview;
        setState({ status: "ready", preview });
        void trackEvent("territory_preview_view", "territory_picker", {
          region,
          service_type: serviceType,
          examples: preview.examples.length,
        });
      })
      .catch((err: unknown) => {
        if ((err as Error)?.name !== "AbortError") setState({ status: "error" });
      });
    return () => controller.abort();
  }, [path, region, serviceType]);

  if (!path || state.status === "idle" || state.status === "off") return null;
  if (state.status === "loading") {
    return (
      <p className={styles.previewLoading} role="status">
        Finding recent CQC changes in {region}…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className={styles.previewLoading} role="status">
        Recent CQC changes could not be loaded. The coverage check above is unaffected.
      </p>
    );
  }

  if (state.status !== "ready") return null;
  const { preview } = state;
  const freshness = freshnessNotice(preview);
  const ratings = ratingNotice(preview);
  // Caveats the notices above already state are not repeated in the list.
  const caveats = preview.caveats.filter((c) => c !== ratings && c !== freshness);
  return (
    <section className={styles.preview} aria-labelledby="territory-preview-heading" data-testid="territory-preview">
      <p className={styles.previewKicker}>Free preview · recent CQC changes</p>
      <h3 id="territory-preview-heading" className={styles.previewHeadline}>
        {previewHeadline(preview)}
      </h3>
      {freshness ? (
        <p className={styles.previewNotice} role="note" data-testid="territory-preview-freshness">
          {freshness}
        </p>
      ) : null}
      {ratings ? (
        <p className={styles.previewNotice} role="note" data-testid="territory-preview-ratings">
          {ratings}
        </p>
      ) : null}
      <p className={styles.resultDetail}>{PREVIEW_SCOPE_NOTE}</p>

      {preview.examples.length ? (
        <ol className={styles.previewList}>
          {preview.examples.map((example) => (
            <li key={example.location_id} className={styles.previewItem}>
              <span
                className={`${styles.previewTag} ${
                  example.signal === "rating_changed" ? styles.previewTagRating : styles.previewTagNew
                }`}
              >
                {signalLabel(example.signal)}
              </span>
              <div className={styles.previewBody}>
                <p className={styles.previewName}>
                  {example.location_name}
                  {example.town ? <span className={styles.previewTown}> · {example.town}</span> : null}
                </p>
                <p className={styles.previewReason}>{example.reason}</p>
                <a className={styles.previewSource} href={example.source_url} target="_blank" rel="noopener noreferrer">
                  CQC record {example.location_id}
                </a>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className={styles.resultDetail}>
          {ratings
            ? "No newly registered locations are recorded for this scope in the window, and rating changes cannot be counted yet."
            : "No newly registered locations or rating changes are recorded for this scope in the window."}{" "}
          A Brief can still rank providers on their current record; we discuss that before any payment.
        </p>
      )}

      <p className={styles.previewFit}>{preview.brief.note}</p>
      <ul className={styles.previewCaveats}>
        {caveats.map((c) => (
          <li key={c}>{c}</li>
        ))}
        <li>
          Window {previewWindowLabel(preview)}. {preview.source.basis}
        </li>
        <li>
          <a href={preview.source.licence_url} target="_blank" rel="noopener noreferrer">
            {preview.source.licence}
          </a>
        </li>
      </ul>
    </section>
  );
}
