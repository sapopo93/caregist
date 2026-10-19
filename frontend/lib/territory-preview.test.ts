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
    notice: null,
    window_anchor: "2026-10-16",
    window_anchor_basis: "",
    freshness_status: "fresh",
    coverage_confirmed: true,
    source_published_at: "2026-10-14",
    reconciled_at: "2026-10-18T01:06:48Z",
    freshness_message: null,
    basis: "",
    licence: "Contains public sector information licensed under the Open Government Licence v3.0.",
    licence_url: "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
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
      note: "We can't yet date rating changes here, so they aren't counted.",
    },
  },
};

const PARTIAL: TerritoryPreview = {
  ...SAMPLE,
  brief: { ...SAMPLE.brief, provisional: true },
  source: {
    ...SAMPLE.source,
    freshness_status: "partial",
    coverage_confirmed: false,
    notice: "Our latest full check of the CQC register hasn't finished, so these figures are provisional and may be incomplete.",
  },
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
      "Across 1,383 providers of domiciliary care in West Midlands: 27 newly registered locations and 3 rating changes in the 90 days to 16 Oct 2026.",
    );
    assert.equal(previewWindowLabel(SAMPLE), "19 Jul 2026 to 16 Oct 2026 (the most recent registration we hold)");
    assert.equal(ratingNotice(SAMPLE), null);
    assert.equal(freshnessNotice(SAMPLE), null);
  });

  it("never turns uncountable rating changes into zero", () => {
    const headline = previewHeadline(UNDATED);
    assert.equal(
      headline,
      "Across 1,383 providers of domiciliary care in West Midlands: 27 newly registered locations in the 90 days to 16 Oct 2026.",
    );
    assert.doesNotMatch(headline, /0 rating|no rating/);
    assert.match(ratingNotice(UNDATED) ?? "", /aren't counted/);
    assert.doesNotMatch(ratingNotice(UNDATED) ?? "", /source|CQC/);
  });

  it("marks partly dated rating counts as a minimum", () => {
    const partial: TerritoryPreview = {
      ...SAMPLE,
      signals: {
        ...SAMPLE.signals,
        rating_changes: { status: "partial", count: 3, undated: 9, note: "We can't yet date 9 rating changes here, so they aren't counted." },
      },
    };
    assert.match(previewHeadline(partial), /at least 3 rating changes/);
    assert.match(ratingNotice(partial) ?? "", /9 rating changes/);
  });

  it("qualifies everything in plain English when source coverage is not confirmed", () => {
    assert.doesNotMatch(freshnessNotice(PARTIAL) ?? "", /status|partial/);
    assert.equal(
      freshnessNotice(PARTIAL),
      "Our latest full check of the CQC register hasn't finished, so these figures are provisional and may be incomplete.",
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
      "Across 1 provider of domiciliary care in West Midlands: no newly registered locations or rating changes in the 90 days to 16 Oct 2026.",
    );
  });

  it("labels signals", () => {
    assert.equal(signalLabel("new_registration"), "New registration");
    assert.equal(signalLabel("rating_changed"), "Rating change");
  });
});
