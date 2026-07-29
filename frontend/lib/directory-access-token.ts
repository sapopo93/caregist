import { createHmac, timingSafeEqual } from "node:crypto";

import type { DirectoryExportScope } from "./directory-export.ts";

const DEFAULT_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7;
const MIN_TOKEN_SECRET_LENGTH = 32;
const MAX_TOKEN_LENGTH = 2048;
const MAX_SCOPE_VALUE_LENGTH = 160;

interface DirectoryTokenPayload extends DirectoryExportScope {
  v: 1;
  iat: number;
  exp: number;
}

function getTokenSecret(): string | null {
  const value = process.env.DIRECTORY_TOKEN_SECRET?.trim();
  return value && value.length >= MIN_TOKEN_SECRET_LENGTH ? value : null;
}

function encodePayload(payload: DirectoryTokenPayload): string {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodePayload(token: string): DirectoryTokenPayload | null {
  try {
    return JSON.parse(Buffer.from(token, "base64url").toString("utf8")) as DirectoryTokenPayload;
  } catch {
    return null;
  }
}

function signPayload(encodedPayload: string, secret: string): string {
  return createHmac("sha256", secret).update(encodedPayload).digest("base64url");
}

function signaturesMatch(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left, "utf8");
  const rightBuffer = Buffer.from(right, "utf8");

  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }

  return timingSafeEqual(leftBuffer, rightBuffer);
}

export function canIssueDirectoryAccessTokens(): boolean {
  return Boolean(getTokenSecret());
}

export function createDirectoryAccessToken(
  scope: DirectoryExportScope,
  options?: { ttlSeconds?: number },
): string {
  const secret = getTokenSecret();
  if (!secret) {
    throw new Error(`DIRECTORY_TOKEN_SECRET must contain at least ${MIN_TOKEN_SECRET_LENGTH} characters.`);
  }
  const scopeValues = [scope.region, scope.serviceType, scope.rating, scope.opportunity ?? ""];
  if (scopeValues.some((value) => typeof value !== "string" || value.length > MAX_SCOPE_VALUE_LENGTH)) {
    throw new Error("Directory export scope is invalid.");
  }

  const issuedAt = Math.floor(Date.now() / 1000);
  const ttlSeconds = options?.ttlSeconds ?? DEFAULT_TOKEN_TTL_SECONDS;
  const payload: DirectoryTokenPayload = {
    v: 1,
    iat: issuedAt,
    exp: issuedAt + ttlSeconds,
    region: scope.region,
    serviceType: scope.serviceType,
    rating: scope.rating,
    opportunity: scope.opportunity ?? "",
  };

  const encodedPayload = encodePayload(payload);
  return `${encodedPayload}.${signPayload(encodedPayload, secret)}`;
}

export function readDirectoryAccessToken(token: string): DirectoryExportScope | null {
  const secret = getTokenSecret();
  if (!secret) {
    return null;
  }

  if (token.length > MAX_TOKEN_LENGTH) {
    return null;
  }

  const segments = token.split(".");
  if (segments.length !== 2) {
    return null;
  }
  const [encodedPayload, providedSignature] = segments;

  const expectedSignature = signPayload(encodedPayload, secret);
  if (!signaturesMatch(providedSignature, expectedSignature)) {
    return null;
  }

  const payload = decodePayload(encodedPayload);
  if (
    !payload ||
    payload.v !== 1 ||
    !Number.isInteger(payload.iat) ||
    !Number.isInteger(payload.exp) ||
    payload.exp <= payload.iat ||
    typeof payload.region !== "string" ||
    typeof payload.serviceType !== "string" ||
    typeof payload.rating !== "string" ||
    (payload.opportunity !== undefined && typeof payload.opportunity !== "string") ||
    [payload.region, payload.serviceType, payload.rating, payload.opportunity ?? ""].some(
      (value) => value.length > MAX_SCOPE_VALUE_LENGTH,
    )
  ) {
    return null;
  }

  const now = Math.floor(Date.now() / 1000);
  if (payload.exp <= now) {
    return null;
  }

  return {
    region: payload.region,
    serviceType: payload.serviceType,
    rating: payload.rating,
    opportunity: payload.opportunity ?? "",
  };
}
