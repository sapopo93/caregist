import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  buildPreviewPath,
  isTerritoryPreviewEnabled,
  previewHeadline,
  previewServiceKey,
  previewWindowLabel,
  signalLabel,
  type TerritoryPreview,
} from "./territory-preview.ts";

const SAMPLE: TerritoryPreview = {
  scope: { kind: "region", name: "West Midlands", service: "homecare", service_label: "Homecare Agencies" },
  organisations: 1383,
  locations: 1587,
  window: { start: "2025-11-23", end: "2026-02-20", days: 90 },
  signals: { new_registrations: 27, rating_changes: 3, organisations_with_signals: 29 },
  examples: [],
  brief: { fits: true, min_organisations: 25, max_organisations: 50, note: "" },
  source: { as_of: "2026-02-20", basis: "" },
  caveats: [],
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
  it("states only the returned counts and the source-anchored window", () => {
    assert.equal(
      previewHeadline(SAMPLE),
      "Across 1,383 homecare organisations in West Midlands: 27 new registrations and 3 rating changes in the 90 days to 20 Feb 2026.",
    );
    assert.equal(previewWindowLabel(SAMPLE), "23 Nov 2025 to 20 Feb 2026");
  });

  it("says plainly when nothing moved", () => {
    const quiet = { ...SAMPLE, organisations: 1, signals: { new_registrations: 0, rating_changes: 0, organisations_with_signals: 0 } };
    assert.equal(
      previewHeadline(quiet),
      "Across 1 homecare organisation in West Midlands: no recorded registrations or rating changes in the 90 days to 20 Feb 2026.",
    );
  });

  it("labels signals", () => {
    assert.equal(signalLabel("new_registration"), "New registration");
    assert.equal(signalLabel("rating_changed"), "Rating change");
  });
});
