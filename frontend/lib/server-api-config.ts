const DEV_API_BASE = "http://localhost:8000";

let hasWarnedServerApiBase = false;
let hasWarnedPublicApiBase = false;
let hasWarnedServerApiKey = false;

function deriveApiBaseFromAppUrl(appUrlRaw: string): string | undefined {
  try {
    const appUrl = new URL(appUrlRaw.startsWith("http") ? appUrlRaw : `https://${appUrlRaw}`);
    if (appUrl.hostname === "caregist.co.uk" || appUrl.hostname === "www.caregist.co.uk") {
      return `${appUrl.protocol}//api.caregist.co.uk`;
    }
  } catch {
    return undefined;
  }

  return undefined;
}

function deriveApiBaseFromConfiguredAppUrl(): string | undefined {
  const candidates = [
    process.env.APP_URL,
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.VERCEL_PROJECT_PRODUCTION_URL,
    process.env.VERCEL_URL,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    const derived = deriveApiBaseFromAppUrl(candidate);
    if (derived) return derived;
  }

  return undefined;
}

function isLocalApiBase(value: string | undefined): boolean {
  if (!value) return false;
  try {
    const url = new URL(value);
    return ["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname);
  } catch {
    return false;
  }
}

function resolveConfiguredApiBase(value: string | undefined, warningFlag: "server_base" | "public_base") {
  if (!value) return undefined;
  const derivedApiBase = deriveApiBaseFromConfiguredAppUrl();
  if (derivedApiBase && isLocalApiBase(value)) {
    warnOnce(
      warningFlag,
      "[caregist] Ignoring localhost API URL for production app URL — deriving API host from app URL",
    );
    return derivedApiBase;
  }
  return value;
}

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

export function getServerApiBase() {
  if (process.env.CAREGIST_BACKEND_URL) return process.env.CAREGIST_BACKEND_URL;
  const configuredApiUrl = resolveConfiguredApiBase(process.env.API_URL, "server_base");
  if (configuredApiUrl) return configuredApiUrl;
  if (process.env.NEXT_PUBLIC_API_URL) {
    const configuredPublicApiUrl = resolveConfiguredApiBase(process.env.NEXT_PUBLIC_API_URL, "server_base");
    if (configuredPublicApiUrl) return configuredPublicApiUrl;
    warnOnce("server_base", "[caregist] API_URL env var is not set — falling back to NEXT_PUBLIC_API_URL");
    return process.env.NEXT_PUBLIC_API_URL;
  }
  const derivedApiBase = deriveApiBaseFromConfiguredAppUrl();
  if (derivedApiBase) {
    warnOnce("server_base", "[caregist] API_URL env var is not set — deriving API host from app URL");
    return derivedApiBase;
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
  if (typeof window === "undefined" && process.env.CAREGIST_BACKEND_URL) {
    return process.env.CAREGIST_BACKEND_URL;
  }
  const configuredPublicApiUrl = resolveConfiguredApiBase(process.env.NEXT_PUBLIC_API_URL, "public_base");
  if (configuredPublicApiUrl) return configuredPublicApiUrl;
  const configuredApiUrl = resolveConfiguredApiBase(process.env.API_URL, "public_base");
  if (configuredApiUrl) return configuredApiUrl;
  const derivedApiBase = deriveApiBaseFromConfiguredAppUrl();
  if (derivedApiBase) {
    warnOnce("public_base", "[caregist] NEXT_PUBLIC_API_URL env var is not set — deriving API host from app URL");
    return derivedApiBase;
  }
  if (typeof window !== "undefined") return "";
  warnOnce("public_base", "[caregist] NEXT_PUBLIC_API_URL env var is not set — falling back to localhost:8000");
  return DEV_API_BASE;
}
