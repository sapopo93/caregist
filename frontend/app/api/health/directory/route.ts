import { NextResponse } from "next/server";

import { canIssueDirectoryAccessTokens } from "@/lib/directory-access-token";
import { getDirectoryDatabaseStatus } from "@/lib/directory-db";
import { hasDirectoryFallbackDataset } from "@/lib/directory-file-store";
import { classifyDirectoryCapabilities } from "@/lib/directory-health";
import { canSendLeadNotifications } from "@/lib/directory-lead-notify";
import { releaseGitSha } from "@/lib/release";

export const runtime = "nodejs";

export async function GET() {
  const [databaseStatus, fallbackDatasetAvailable] = await Promise.all([
    getDirectoryDatabaseStatus(),
    hasDirectoryFallbackDataset(),
  ]);
  const databaseAvailable = databaseStatus.available;
  const { status, operatingMode, readMode, writeMode } = classifyDirectoryCapabilities({
    databaseAvailable,
    fallbackDatasetAvailable,
    tokenIssuanceAvailable: canIssueDirectoryAccessTokens(),
  });
  const notificationMode = canSendLeadNotifications() ? "email" : "log-only";

  return NextResponse.json({
    status,
    checkedAt: new Date().toISOString(),
    release: { gitSha: releaseGitSha() },
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
