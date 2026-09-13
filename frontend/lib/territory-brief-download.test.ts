import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { test } from "node:test";
import { consumeTerritoryBriefDownload } from "./territory-brief-download.ts";

test("invalid bearer tokens never reach the database", async () => {
  for (const token of ["", "guess", "../private.pdf", "x".repeat(1000)]) {
    assert.equal(await consumeTerritoryBriefDownload(token, async () => { throw new Error("queried"); }), null);
  }
});

test("only the token hash reaches the database and missing entitlements deny access", async () => {
  const token = "a".repeat(43);
  const result = await consumeTerritoryBriefDownload(token, async (_sql, values) => {
    assert.deepEqual(values, [createHash("sha256").update(token).digest("hex")]);
    return { rows: [] };
  });
  assert.equal(result, null);
});

test("returns the entitled artifact without accepting a client-selected path", async () => {
  const artifact = { blob_pathname: "territory-briefs/order/private/brief.pdf", filename: "territory-opportunity-brief.pdf", content_type: "application/pdf" };
  assert.deepEqual(await consumeTerritoryBriefDownload("a".repeat(43), async () => ({ rows: [artifact] })), artifact);
});
