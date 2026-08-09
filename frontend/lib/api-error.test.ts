import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { apiErrorMessage, describeFetchError, normalizeApiError } from "./api-error.ts";

describe("apiErrorMessage", () => {
  it("returns a string detail", () => {
    assert.equal(apiErrorMessage({ detail: "Email already registered." }, "Fallback"), "Email already registered.");
  });

  it("flattens FastAPI validation errors without rendering objects", () => {
    assert.equal(
      apiErrorMessage(
        {
          detail: [
            { loc: ["body", "email"], msg: "Value is not a valid email address", type: "value_error" },
            { loc: ["body", "password"], msg: "Password is too short", type: "value_error" },
          ],
        },
        "Registration failed.",
      ),
      "Value is not a valid email address Password is too short",
    );
  });

  it("uses the safe fallback for unknown payloads", () => {
    assert.equal(apiErrorMessage({ detail: { unexpected: true } }, "Registration failed."), "Registration failed.");
  });
});

describe("normalizeApiError", () => {
  it("returns the string detail as the message", () => {
    const info = normalizeApiError(401, { detail: "Invalid email or password." }, "fallback");
    assert.equal(info.message, "Invalid email or password.");
    assert.equal(info.isUnverifiedEmail, false);
    assert.equal(info.isServerError, false);
  });

  it("flags the exact unverified-email message", () => {
    const info = normalizeApiError(403, { detail: "Verify your email before logging in." }, "fallback");
    assert.equal(info.isUnverifiedEmail, true);
  });

  it("does NOT flag a reworded verification message (exact match only)", () => {
    const info = normalizeApiError(403, { detail: "Please confirm your email address." }, "fallback");
    assert.equal(info.isUnverifiedEmail, false);
  });

  it("formats pydantic validation arrays with field names", () => {
    const info = normalizeApiError(
      422,
      { detail: [
        { loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" },
        { loc: ["body", "password"], msg: "field required", type: "missing" },
      ]},
      "fallback",
    );
    assert.equal(info.message, "email: value is not a valid email address; password: field required");
    assert.equal(info.isUnverifiedEmail, false);
  });

  it("tolerates non-string msg values in pydantic arrays", () => {
    const info = normalizeApiError(422, { detail: [{ loc: ["body"], msg: null }] }, "fallback");
    assert.equal(info.message, "fallback");
  });

  it("treats 5xx as server error regardless of body", () => {
    const info = normalizeApiError(502, { detail: "Bad Gateway" }, "fallback");
    assert.equal(info.isServerError, true);
    assert.match(info.message, /temporarily unavailable/);
  });

  it("treats unparseable body on 500 as server error", () => {
    const info = normalizeApiError(500, {}, "fallback");
    assert.equal(info.isServerError, true);
    assert.match(info.message, /temporarily unavailable/);
  });

  it("flags 409 conflict", () => {
    const info = normalizeApiError(409, { detail: "Email already registered." }, "fallback");
    assert.equal(info.isConflict, true);
    assert.equal(info.message, "Email already registered.");
  });

  it("flags 429 rate limit", () => {
    const info = normalizeApiError(429, { detail: "Invalid email or password." }, "fallback");
    assert.equal(info.isRateLimited, true);
  });

  it("falls back when detail is missing entirely", () => {
    const info = normalizeApiError(400, {}, "fallback");
    assert.equal(info.message, "fallback");
  });

  it("falls back when detail is an empty array", () => {
    const info = normalizeApiError(422, { detail: [] }, "fallback");
    assert.equal(info.message, "fallback");
  });

  it("does not crash on null data", () => {
    const info = normalizeApiError(400, null, "fallback");
    assert.equal(info.message, "fallback");
  });
});

describe("describeFetchError", () => {
  it("identifies network failure", () => {
    assert.match(describeFetchError(new TypeError("Failed to fetch")), /Network error/);
  });

  it("returns generic message for other errors", () => {
    assert.match(describeFetchError(new Error("boom")), /Something went wrong/);
  });

  it("handles non-Error values", () => {
    assert.match(describeFetchError(undefined), /Something went wrong/);
  });
});
