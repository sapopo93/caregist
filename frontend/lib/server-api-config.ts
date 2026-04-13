import fs from "node:fs";
import path from "node:path";

const DEV_API_BASE = "http://localhost:8000";

let hasWarnedServerApiBase = false;
let hasWarnedPublicApiBase = false;
let hasWarnedServerApiKey = false;
let rootEnvCache: Record<string, string> | null = null;

function warnOnce(flag: "server_base" | "server_key" | "public_base", message: string) {
  if (flag === "server_base" && !hasWarnedServerApiBase) {
    hasWarnedServerApiBase = true;
    console.warn(message);
  }
  if (flag === "server_key" && !hasWarnedServerApiKey) {
    hasWarnedServerApiKey = true;
    console.warn(message);
  }
  if (flag === "public_base" && !hasWarnedPublicApiBase) {
    hasWarnedPublicApiBase = true;
    console.warn(message);
  }
}

function readRootEnvVar(key: string): string | undefined {
  if (typeof window !== "undefined") return undefined;
  if (rootEnvCache) return rootEnvCache[key];

  rootEnvCache = {};
  const candidates = [
    path.resolve(process.cwd(), ".env"),
    path.resolve(process.cwd(), "..", ".env"),
  ];

  for (const envPath of candidates) {
    if (!fs.existsSync(envPath)) continue;
    for (const line of fs.readFileSync(envPath, "utf-8").split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
      const [rawKey, ...rest] = trimmed.split("=");
      const rawValue = rest.join("=");
      if (rawKey && !(rawKey in rootEnvCache)) {
        rootEnvCache[rawKey] = rawValue.trim().replace(/^['"]|['"]$/g, "");
      }
    }
  }

  return rootEnvCache[key];
}

export function getServerApiBase() {
  if (process.env.API_URL) return process.env.API_URL;
  if (process.env.NEXT_PUBLIC_API_URL) {
    warnOnce("server_base", "[caregist] API_URL env var is not set — falling back to NEXT_PUBLIC_API_URL");
    return process.env.NEXT_PUBLIC_API_URL;
  }
  const rootApiUrl = readRootEnvVar("API_URL");
  if (rootApiUrl) {
    warnOnce("server_base", "[caregist] API_URL env var is not set in frontend config — falling back to repo root .env");
    return rootApiUrl;
  }
  if (process.env.APP_URL) {
    warnOnce("server_base", "[caregist] API_URL env var is not set — falling back to APP_URL");
    return process.env.APP_URL;
  }
  warnOnce("server_base", "[caregist] API_URL env var is not set — falling back to localhost:8000");
  return DEV_API_BASE;
}

export function getServerApiKey() {
  if (process.env.API_KEY) return process.env.API_KEY;
  if (process.env.API_MASTER_KEY) {
    warnOnce("server_key", "[caregist] API_KEY env var is not set — falling back to API_MASTER_KEY");
    return process.env.API_MASTER_KEY;
  }

  const rootApiKey = readRootEnvVar("API_KEY");
  if (rootApiKey) {
    warnOnce("server_key", "[caregist] API_KEY env var is not set in frontend config — falling back to repo root .env");
    return rootApiKey;
  }

  const rootMasterKey = readRootEnvVar("API_MASTER_KEY");
  if (rootMasterKey) {
    warnOnce("server_key", "[caregist] API_KEY env var is not set — falling back to API_MASTER_KEY from repo root .env");
    return rootMasterKey;
  }

  if (process.env.NEXT_PUBLIC_API_KEY) {
    warnOnce(
      "server_key",
      "[caregist] Falling back to NEXT_PUBLIC_API_KEY for server requests. Rotate this key and move it to API_KEY or API_MASTER_KEY.",
    );
    return process.env.NEXT_PUBLIC_API_KEY;
  }

  throw new Error("[caregist] API_KEY or API_MASTER_KEY env var is required but not set");
}

export function getPublicApiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (process.env.API_URL) return process.env.API_URL;
  if (typeof window !== "undefined") return "";
  warnOnce("public_base", "[caregist] NEXT_PUBLIC_API_URL env var is not set — falling back to localhost:8000");
  return DEV_API_BASE;
}
