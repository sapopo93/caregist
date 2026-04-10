const DEV_API_BASE = "http://localhost:8000";
const DEV_API_KEY = "dev_key_change_me";

let hasWarnedServerApiBase = false;
let hasWarnedServerApiKey = false;
let hasWarnedPublicApiBase = false;

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
  if (process.env.API_URL) return process.env.API_URL;
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (process.env.APP_URL) {
    try {
      const appUrl = new URL(process.env.APP_URL);
      if (appUrl.hostname === "caregist.co.uk" || appUrl.hostname === "www.caregist.co.uk") {
        return `${appUrl.protocol}//api.caregist.co.uk`;
      }
    } catch {
      // Fall through to the development default below.
    }
  }
  warnOnce("server_base", "[caregist] API_URL env var is not set — falling back to localhost:8000");
  return DEV_API_BASE;
}

export function getServerApiKey() {
  if (process.env.API_KEY) return process.env.API_KEY;
  if (process.env.API_MASTER_KEY) return process.env.API_MASTER_KEY;
  warnOnce("server_key", "[caregist] API_KEY env var is not set — using default dev key");
  return DEV_API_KEY;
}

export function getPublicApiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (process.env.API_URL) return process.env.API_URL;
  if (typeof window !== "undefined") return "";
  warnOnce("public_base", "[caregist] NEXT_PUBLIC_API_URL env var is not set — falling back to localhost:8000");
  return DEV_API_BASE;
}
