import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { apiErrorMessage } from "./api-error.ts";

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
