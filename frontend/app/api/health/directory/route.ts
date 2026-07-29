import { NextResponse } from "next/server";

import { canIssueDirectoryAccessTokens } from "@/lib/directory-access-token";
import { getDirectoryDatabaseStatus } from "@/lib/directory-db";
import { hasDirectoryFallbackDataset } from "@/lib/directory-file-store";
import { canSendLeadNotifications } from "@/lib/directory-lead-notify";

export const runtime = "nodejs";

export async function GET() {
  const [databaseStatus, fallbackDatasetAvailable] = await Promise.all([
    getDirectoryDatabaseStatus(),
    hasDirectoryFallbackDataset(),
  ]);
  const databaseAvailable = databaseStatus.available;

  const readMode = databaseAvailable ? "database" : fallbackDatasetAvailable ? "full-dataset-fallback" : "unavailable";
  const writeMode = databaseAvailable ? "database" : canIssueDirectoryAccessTokens() ? "stateless-token" : "unavailable";
  const notificationMode = canSendLeadNotifications() ? "email" : "log-only";
  const operatingMode = databaseAvailable ? "database" : readMode === "full-dataset-fallback" ? "fallback" : "unavailable";
  const status =
    readMode === "unavailable" || writeMode === "unavailable"
      ? "down"
      : databaseAvailable
        ? "ok"
        : "degraded";

  return NextResponse.json({
    status,
    checkedAt: new Date().toISOString(),
    capabilities: {
      operatingMode,
      readMode,
      writeMode,
      notificationMode,
      fallbackDatasetAvailable,
      databaseAvailable,
      databaseReason: databaseStatus.reason,
    },
  });
}
