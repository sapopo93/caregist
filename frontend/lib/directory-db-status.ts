export type DirectoryDatabaseFailureReason =
  | "ok"
  | "not_configured"
  | "auth_failed"
  | "quota_exceeded"
  | "connection_failed"
  | "unknown";

export interface DirectoryDatabaseStatus {
  available: boolean;
  reason: DirectoryDatabaseFailureReason;
}

export function classifyDirectoryDatabaseError(error: unknown): DirectoryDatabaseFailureReason {
  const message = error instanceof Error ? error.message.toLowerCase() : String(error ?? "").toLowerCase();

  if (message.includes("not configured")) {
    return "not_configured";
  }

  if (message.includes("password authentication failed")) {
    return "auth_failed";
  }

  if (message.includes("exceeded the compute time quota")) {
    return "quota_exceeded";
  }

  if (
    message.includes("timeout") ||
    message.includes("econnrefused") ||
    message.includes("enotfound") ||
    message.includes("server closed the connection unexpectedly") ||
    message.includes("connection terminated unexpectedly")
  ) {
    return "connection_failed";
  }

  return "unknown";
}
