import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";

import { buildNotQuarantinedClause } from "./directory-query-clauses.ts";

const directoryDbSource = readFileSync(new URL("./directory-db.ts", import.meta.url), "utf8");
const coverageRouteSource = readFileSync(
  new URL("../app/api/territory/coverage/route.ts", import.meta.url),
  "utf8",
);

function functionBody(source: string, name: string): string {
  const start = source.indexOf(`export async function ${name}(`);
  assert.notEqual(start, -1, `${name} not found`);
  const next = source.indexOf("\nexport ", start + 1);
  return source.slice(start, next === -1 ? undefined : next);
}

describe("quarantined locations clause", () => {
  it("excludes only unresolved quarantine rows matched on the CQC location id", () => {
    const clause = buildNotQuarantinedClause();

    assert.match(clause, /^NOT EXISTS \(/);
    assert.match(clause, /FROM reconciliation_quarantined_locations q/);
    assert.match(clause, /q\.location_id = care_providers\.id/);
    assert.match(clause, /q\.resolved_at IS NULL/);
  });

  it("can target an aliased providers table", () => {
    assert.match(buildNotQuarantinedClause("cp"), /q\.location_id = cp\.id/);
  });

  it("has no table-existence guard, so a missing table errors instead of counting everything", () => {
    assert.doesNotMatch(buildNotQuarantinedClause(), /to_regclass|information_schema/i);
  });
});

describe("territory coverage check", () => {
  const body = functionBody(directoryDbSource, "getTerritoryScopeCoverage");

  it("adds the quarantine exclusion to the counted and dated row set", () => {
    assert.match(body, /clauses\.push\(buildNotQuarantinedClause\(\)\)/);
    const pushAt = body.indexOf("buildNotQuarantinedClause()");
    const queryAt = body.indexOf("getSql().query");
    assert.ok(pushAt > -1 && pushAt < queryAt, "exclusion must be added before the query runs");
    assert.match(body, /WHERE \$\{clauses\.join\(" AND "\)\}/);
  });

  it("does not swallow database errors, so a missing quarantine table fails closed", () => {
    assert.doesNotMatch(body, /\bcatch\b/);
    assert.doesNotMatch(body, /Fallback/);
  });

  it("returns 503 from the coverage route when the coverage query throws", () => {
    assert.match(coverageRouteSource, /await getTerritoryScopeCoverage\(/);
    assert.match(coverageRouteSource, /catch \{[\s\S]*?status: 503/);
  });

  it("leaves the shared directory WHERE builder unchanged", () => {
    const builder = directoryDbSource.slice(
      directoryDbSource.indexOf("function buildWhereClause("),
      directoryDbSource.indexOf("function buildSearchSql("),
    );
    assert.ok(builder.length > 0);
    assert.doesNotMatch(builder, /buildNotQuarantinedClause/);
  });
});
