export type DirectoryReadMode = "database" | "full-dataset-fallback" | "unavailable";
export type DirectoryWriteMode = "database" | "stateless-token" | "unavailable";
export type DirectoryOperatingMode = "database" | "fallback" | "unavailable";
export type DirectoryHealthStatus = "ok" | "degraded" | "down";

interface DirectoryCapabilityInputs {
  databaseAvailable: boolean;
  fallbackDatasetAvailable: boolean;
  tokenIssuanceAvailable: boolean;
}

interface DirectoryCapabilities {
  status: DirectoryHealthStatus;
  operatingMode: DirectoryOperatingMode;
  readMode: DirectoryReadMode;
  writeMode: DirectoryWriteMode;
}

export function classifyDirectoryCapabilities({
  databaseAvailable,
  fallbackDatasetAvailable,
  tokenIssuanceAvailable,
}: DirectoryCapabilityInputs): DirectoryCapabilities {
  const readMode = databaseAvailable
    ? "database"
    : fallbackDatasetAvailable
      ? "full-dataset-fallback"
      : "unavailable";
  const writeMode = databaseAvailable
    ? "database"
    : tokenIssuanceAvailable
      ? "stateless-token"
      : "unavailable";
  const operatingMode = databaseAvailable
    ? "database"
    : readMode === "full-dataset-fallback"
      ? "fallback"
      : "unavailable";
  const status = readMode === "unavailable" ? "down" : databaseAvailable ? "ok" : "degraded";

  return { status, operatingMode, readMode, writeMode };
}
