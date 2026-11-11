import assert from "node:assert/strict";
import { test } from "node:test";

import { redactAnalyticsUrl } from "./analytics-url.ts";

test("drops tokens and emails from the query string", () => {
  assert.equal(
    redactAnalyticsUrl("https://www.caregist.co.uk/verify-email?token=abc&email=a%40b.com"),
    "https://www.caregist.co.uk/verify-email",
  );
});

test("keeps utm parameters for campaign attribution", () => {
  assert.equal(
    redactAnalyticsUrl("https://www.caregist.co.uk/?utm_source=email&code=123&utm_campaign=nov"),
    "https://www.caregist.co.uk/?utm_source=email&utm_campaign=nov",
  );
});

test("drops the fragment", () => {
  assert.equal(redactAnalyticsUrl("https://www.caregist.co.uk/search#top"), "https://www.caregist.co.uk/search");
});

test("falls back to stripping on a relative or invalid url", () => {
  assert.equal(redactAnalyticsUrl("/reset-password?code=9#x"), "/reset-password");
});
