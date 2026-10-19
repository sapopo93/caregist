import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  buildPreviewPath,
  freshnessNotice,
  isTerritoryPreviewEnabled,
  previewHeadline,
  previewServiceKey,
  previewWindowLabel,
  ratingNotice,
  signalLabel,
  type TerritoryPreview,
} from "./territory-preview.ts";

const SAMPLE: TerritoryPreview = {
  scope: { kind: "region", name: "West Midlands", service: "homecare", service_label: "Home Care" },
  organisations: 1383,
  locations: 1587,
  window: { start: "2026-07-19", end: "2026-10-16", days: 90 },
  signals: {
    new_registrations: 27,
    rating_changes: { status: "available", count: 3, undated: 0 },
    organisations_with_signals: 29,
  },
  examples: [],
  brief: { fits: true, provisional: false, min_organisations: 25, max_organisations: 50, note: "" },
  source: {
    window_anchor: "2026-10-16",
    window_anchor_basis: "",
    freshness_status: "fresh",
    coverage_confirmed: true,
    source_published_at: "2026-10-14",
    reconciled_at: "2026-10-18T01:06:48Z",
    freshness_message: null,
    basis: "",
  },
  caveats: [],
};

const UNDATED: TerritoryPreview = {
  ...SAMPLE,
  signals: {
    ...SAMPLE.signals,
    rating_changes: {
      status: "unavailable",
      count: null,
      undated: 34332,
      note: "Rating-change dates are not available from the source, so rating changes in this window cannot be counted.",
    },
  },
};

const PARTIAL: TerritoryPreview = {
  ...SAMPLE,
  brief: { ...SAMPLE.brief, provisional: true },
  source: { ...SAMPLE.source, freshness_status: "partial", coverage_confirmed: false },
};

describe("territory preview flag", () => {
  it("is off unless explicitly 'true'", () => {
    assert.equal(isTerritoryPreviewEnabled(undefined), false);
    assert.equal(isTerritoryPreviewEnabled(""), false);
    assert.equal(isTerritoryPreviewEnabled("1"), false);
    assert.equal(isTerritoryPreviewEnabled("TRUE"), true);
  });
});

describe("territory preview request", () => {
  it("maps the four care services and treats an empty filter as all services", () => {
    assert.equal(previewServiceKey("Homecare Agencies"), "homecare");
    assert.equal(previewServiceKey("Supported Living"), "supported_living");
    assert.equal(previewServiceKey(""), null);
    assert.equal(previewServiceKey("Dentist"), undefined);
  });

  it("builds an encoded region path and skips unsupported services", () => {
    assert.equal(
      buildPreviewPath("West Midlands", "Nursing Homes"),
      "/api/v1/territory-preview?kind=region&name=West+Midlands&service=nursing",
    );
    assert.equal(buildPreviewPath("London", ""), "/api/v1/territory-preview?kind=region&name=London");
    assert.equal(buildPreviewPath("London", "Dentist"), null);
    assert.equal(buildPreviewPath(" ", ""), null);
  });
});

describe("territory preview copy", () => {
  it("states measured counts in provider language with the window end", () => {
    assert.equal(
      previewHeadline(SAMPLE),
      "Across 1,383 homecare providers in West Midlands: 27 new registrations and 3 rating changes recorded in the 90 days to 16 Oct 2026.",
    );
    assert.equal(previewWindowLabel(SAMPLE), "19 Jul 2026 to 16 Oct 2026, ending at the latest recorded registration");
    assert.equal(ratingNotice(SAMPLE), null);
    assert.equal(freshnessNotice(SAMPLE), null);
  });

  it("never turns uncountable rating changes into zero", () => {
    const headline = previewHeadline(UNDATED);
    assert.equal(
      headline,
      "Across 1,383 homecare providers in West Midlands: 27 new registrations recorded in the 90 days to 16 Oct 2026.",
    );
    assert.doesNotMatch(headline, /0 rating|no rating/);
    assert.match(ratingNotice(UNDATED) ?? "", /cannot be counted/);
  });

  it("marks partly dated rating counts as a minimum", () => {
    const partial: TerritoryPreview = {
      ...SAMPLE,
      signals: {
        ...SAMPLE.signals,
        rating_changes: { status: "partial", count: 3, undated: 9, note: "9 rating changes in this scope have no source date and are not counted." },
      },
    };
    assert.match(previewHeadline(partial), /at least 3 rating changes/);
    assert.match(ratingNotice(partial) ?? "", /9 rating changes/);
  });

  it("qualifies everything when source coverage is not confirmed", () => {
    assert.equal(
      freshnessNotice(PARTIAL),
      "Provisional: CQC source coverage cannot currently be confirmed (status: partial). The latest CQC source was published 14 Oct 2026. Counts may be incomplete or out of date.",
    );
  });

  it("says plainly when nothing was recorded", () => {
    const quiet: TerritoryPreview = {
      ...SAMPLE,
      organisations: 1,
      signals: { new_registrations: 0, rating_changes: { status: "available", count: 0, undated: 0 }, organisations_with_signals: 0 },
    };
    assert.equal(
      previewHeadline(quiet),
      "Across 1 homecare provider in West Midlands: no new registrations or rating changes recorded in the 90 days to 16 Oct 2026.",
    );
  });

  it("labels signals", () => {
    assert.equal(signalLabel("new_registration"), "New registration");
    assert.equal(signalLabel("rating_changed"), "Rating change");
  });
});
