import test from "node:test";
import assert from "node:assert/strict";

import { classifyDirectoryCapabilities } from "./directory-health.ts";

test("directory capability status follows readable customer paths while writes fail closed", () => {
  assert.deepEqual(
    classifyDirectoryCapabilities({
      databaseAvailable: false,
      fallbackDatasetAvailable: true,
      tokenIssuanceAvailable: false,
    }),
    {
      status: "degraded",
      operatingMode: "fallback",
      readMode: "full-dataset-fallback",
      writeMode: "unavailable",
    },
  );

  assert.deepEqual(
    classifyDirectoryCapabilities({
      databaseAvailable: false,
      fallbackDatasetAvailable: false,
      tokenIssuanceAvailable: true,
    }),
    {
      status: "down",
      operatingMode: "unavailable",
      readMode: "unavailable",
      writeMode: "stateless-token",
    },
  );

  assert.deepEqual(
    classifyDirectoryCapabilities({
      databaseAvailable: true,
      fallbackDatasetAvailable: false,
      tokenIssuanceAvailable: false,
    }),
    {
      status: "ok",
      operatingMode: "database",
      readMode: "database",
      writeMode: "database",
    },
  );
});
