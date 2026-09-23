import { createHmac } from "node:crypto";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_CONTACT_LENGTH = 160;
const MIN_SECRET_LENGTH = 32;
const DEDUPE_WINDOW_MS = 15 * 60 * 1000;

export interface TerritoryScopeRequestContact {
  email: string;
  name: string;
  company: string;
}

export interface TerritoryScopeRequestSecurityIdentity {
  requesterFingerprint: string;
  submissionKey: string;
}

export function normalizeTerritoryScopeRequestContact(input: {
  email?: unknown;
  name?: unknown;
  company?: unknown;
}): TerritoryScopeRequestContact {
  const email = String(input.email ?? "").trim().toLowerCase();
  const name = String(input.name ?? "").trim();
  const company = String(input.company ?? "").trim();

  if (!EMAIL_RE.test(email) || email.length > MAX_CONTACT_LENGTH) {
    throw new Error("Enter a valid work email address.");
  }
  if ([name, company].some((value) => value.length > MAX_CONTACT_LENGTH)) {
    throw new Error("A contact field is too long.");
  }
  return { email, name, company };
}

function getRequestSource(request: Request): string {
  if (process.env.VERCEL === "1") {
    return (
      request.headers.get("x-vercel-forwarded-for")?.split(",")[0]?.trim() ||
      request.headers.get("x-real-ip")?.trim() ||
      "unknown"
    );
  }
  return "unknown";
}

export function createTerritoryScopeRequestSecurityIdentity(
  request: Request,
  input: TerritoryScopeRequestContact & { region: string; buyerType: string; serviceType: string },
  now = Date.now(),
): TerritoryScopeRequestSecurityIdentity {
  const secret = process.env.DIRECTORY_TOKEN_SECRET?.trim();
  if (!secret || secret.length < MIN_SECRET_LENGTH) {
    throw new Error(`DIRECTORY_TOKEN_SECRET must contain at least ${MIN_SECRET_LENGTH} characters.`);
  }

  const hmac = (value: string) => createHmac("sha256", secret).update(value).digest("hex");
  const requesterFingerprint = hmac(`territory-scope-source:${getRequestSource(request)}`);
  const window = Math.floor(now / DEDUPE_WINDOW_MS);
  const submissionKey = hmac(
    ["territory-scope-submission", window, input.email, input.region, input.buyerType, input.serviceType]
      .join(":"),
  );
  return { requesterFingerprint, submissionKey };
}
