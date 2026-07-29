import test from "node:test";
import assert from "node:assert/strict";

import { classifyDirectoryDatabaseError } from "./directory-db-status.ts";

test("classifyDirectoryDatabaseError identifies configuration errors", () => {
  assert.equal(
    classifyDirectoryDatabaseError(new Error("POSTGRES_URL or DATABASE_URL is not configured.")),
    "not_configured",
  );
});

test("classifyDirectoryDatabaseError identifies auth failures", () => {
  assert.equal(
    classifyDirectoryDatabaseError(new Error("password authentication failed for user 'neondb_owner'")),
    "auth_failed",
  );
});

test("classifyDirectoryDatabaseError identifies Neon compute quota failures", () => {
  assert.equal(
    classifyDirectoryDatabaseError(new Error("Your account or project has exceeded the compute time quota.")),
    "quota_exceeded",
  );
});

test("classifyDirectoryDatabaseError identifies connection failures", () => {
  assert.equal(
    classifyDirectoryDatabaseError(new Error("connect timeout while reaching postgres.example.com")),
    "connection_failed",
  );
});

test("classifyDirectoryDatabaseError falls back to unknown", () => {
  assert.equal(classifyDirectoryDatabaseError(new Error("unexpected postgres failure")), "unknown");
});
