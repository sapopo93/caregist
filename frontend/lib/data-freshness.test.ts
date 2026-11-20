import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { describeDirectoryFreshness, formatDate, formatFreshnessDay, type SourceStatus } from "./data-freshness.ts";

const DATED: SourceStatus = {
  sourcePublishedAt: "2026-11-04",
  sourceRetrievedAt: "2026-11-08T03:15:00Z",
};

const BANNED = /\b(current|currently|live)\b|up to date|up-to-date/i;

describe("formatFreshnessDay", () => {
  it("formats a calendar date and a timestamp as long UK dates", () => {
    assert.equal(formatFreshnessDay("2026-11-04"), "4 November 2026");
    assert.equal(formatFreshnessDay("2026-11-08T03:15:00Z"), "8 November 2026");
  });

  it("uses the UK calendar day for a timestamp near midnight", () => {
    assert.equal(formatFreshnessDay("2026-07-01T23:30:00Z"), "2 July 2026");
  });

  it("returns null for missing or unreadable values", () => {
    assert.equal(formatFreshnessDay(null), null);
    assert.equal(formatFreshnessDay(undefined), null);
    assert.equal(formatFreshnessDay(""), null);
    assert.equal(formatFreshnessDay("not a date"), null);
  });
});

describe("formatDate (data-status page)", () => {
  it("keeps the existing data-status behaviour", () => {
    assert.equal(formatDate(null), "Not available");
    assert.equal(formatDate("2026-11-04"), "4 November 2026");
    assert.equal(formatDate("garbage"), "garbage");
    assert.match(formatDate("2026-11-08T03:15:00Z"), /^8 November 2026/);
  });
});

describe("describeDirectoryFreshness", () => {
  it("states both dates without a warning when fresh", () => {
    const result = describeDirectoryFreshness({ ...DATED, status: "fresh" });
    assert.equal(result.tone, "ok");
    assert.equal(
      result.text,
      "CareGist last checked CQC's directory on 8 November 2026. The edition it holds was published on 4 November 2026.",
    );
  });

  it("warns when stale", () => {
    const result = describeDirectoryFreshness({ ...DATED, status: "stale" });
    assert.equal(result.tone, "warning");
    assert.equal(
      result.text,
      "This directory may be out of date. It is based on CQC's 4 November 2026 edition, last checked by CareGist on 8 November 2026.",
    );
  });

  it("warns when partial or unknown", () => {
    for (const status of ["partial", "unknown"] as const) {
      const result = describeDirectoryFreshness({ ...DATED, status });
      assert.equal(result.tone, "warning");
      assert.match(result.text, /^This directory may be out of date\. It is based on CQC's 4 November 2026 edition/);
    }
  });

  it("warns when the status field is absent or not recognised", () => {
    assert.equal(describeDirectoryFreshness({ ...DATED }).tone, "warning");
    assert.equal(describeDirectoryFreshness({ ...DATED, status: "something-new" as never }).tone, "warning");
  });

  it("says it could not confirm recency when the API was unreachable", () => {
    assert.deepEqual(describeDirectoryFreshness(null), {
      tone: "warning",
      text: "CareGist could not confirm how recent this directory is.",
    });
  });

  it("omits a missing date rather than inventing one", () => {
    const onlyPublished = describeDirectoryFreshness({ status: "stale", sourcePublishedAt: "2026-11-04" });
    assert.equal(onlyPublished.text, "This directory may be out of date. It is based on CQC's 4 November 2026 edition.");

    const onlyChecked = describeDirectoryFreshness({ status: "stale", sourceRetrievedAt: "2026-11-08T03:15:00Z" });
    assert.equal(onlyChecked.text, "This directory may be out of date. CareGist last checked CQC's directory on 8 November 2026.");

    const neither = describeDirectoryFreshness({ status: "unknown" });
    assert.equal(neither.text, "This directory may be out of date.");

    const freshOnlyChecked = describeDirectoryFreshness({ status: "fresh", sourceRetrievedAt: "2026-11-08T03:15:00Z" });
    assert.deepEqual(freshOnlyChecked, { tone: "ok", text: "CareGist last checked CQC's directory on 8 November 2026." });

    const freshOnlyPublished = describeDirectoryFreshness({ status: "fresh", sourcePublishedAt: "2026-11-04" });
    assert.deepEqual(freshOnlyPublished, { tone: "ok", text: "The CQC edition CareGist holds was published on 4 November 2026." });
  });

  it("does not show a fresh status as reassurance when it has no dates", () => {
    const result = describeDirectoryFreshness({ status: "fresh" });
    assert.equal(result.tone, "warning");
    assert.equal(result.text, "CareGist could not confirm how recent this directory is.");
  });

  it("treats an unreadable date as missing", () => {
    const result = describeDirectoryFreshness({ status: "stale", sourcePublishedAt: "soon", sourceRetrievedAt: "2026-11-08" });
    assert.equal(result.text, "This directory may be out of date. CareGist last checked CQC's directory on 8 November 2026.");
  });

  it("never describes the data as current, live or up to date", () => {
    const statuses: Array<SourceStatus | null> = [
      null,
      {},
      { status: "fresh" },
      { status: "fresh", ...DATED, message: "Data is current and live" },
      { status: "stale", ...DATED, message: "Data is up to date" },
      { status: "partial", ...DATED },
      { status: "unknown" },
      { status: "stale", sourcePublishedAt: "2026-11-04" },
      { status: "stale", sourceRetrievedAt: "2026-11-08T03:15:00Z" },
    ];
    for (const status of statuses) {
      assert.doesNotMatch(describeDirectoryFreshness(status).text, BANNED);
    }
  });
});
