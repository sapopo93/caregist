import { createHmac } from "node:crypto";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const IDEMPOTENCY_KEY_RE = /^[A-Za-z0-9_-]{20,128}$/;
const MAX_CONTACT_LENGTH = 160;
const MIN_SECRET_LENGTH = 32;

export interface TerritoryScopeRequestContact {
  email: string;
  name: string;
  company: string;
}

export interface TerritoryScopeRequestSecurityIdentity {
  requesterFingerprint: string;
  contactFingerprint: string;
  submissionKey: string;
}

export class TerritoryScopeRequestInputError extends Error {}

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
): TerritoryScopeRequestSecurityIdentity {
  const secret = process.env.DIRECTORY_TOKEN_SECRET?.trim();
  if (!secret || secret.length < MIN_SECRET_LENGTH) {
    throw new Error(`DIRECTORY_TOKEN_SECRET must contain at least ${MIN_SECRET_LENGTH} characters.`);
  }

  const hmac = (value: string) => createHmac("sha256", secret).update(value).digest("hex");
  const requesterFingerprint = hmac(`territory-scope-source:${getRequestSource(request)}`);
  const idempotencyKey = request.headers.get("idempotency-key")?.trim() ?? "";
  if (!IDEMPOTENCY_KEY_RE.test(idempotencyKey)) {
    throw new TerritoryScopeRequestInputError("Send a valid Idempotency-Key header.");
  }
  const contactFingerprint = hmac(`territory-scope-contact:${input.email}`);
  const submissionKey = hmac(
    ["territory-scope-submission", idempotencyKey, requesterFingerprint, input.email, input.region, input.buyerType, input.serviceType]
      .join(":"),
  );
  return { requesterFingerprint, contactFingerprint, submissionKey };
}
