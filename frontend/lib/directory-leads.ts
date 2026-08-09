import { isDirectoryOpportunity, type DirectoryOpportunity } from "./directory-constants.ts";

export interface NormalizedLeadRequest {
  email: string;
  region: string;
  serviceType: string;
  rating: string;
  opportunity: DirectoryOpportunity | "";
}

const MAX_EMAIL_LENGTH = 254;
const MAX_FILTER_LENGTH = 160;

function normalizeText(value: string | undefined): string {
  return String(value ?? "").trim();
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function normalizeLeadRequest(input: {
  email?: string;
  region?: string;
  serviceType?: string;
  rating?: string;
  opportunity?: string;
}): NormalizedLeadRequest {
  const email = normalizeText(input.email).toLowerCase();
  if (!email) {
    throw new Error("Email is required.");
  }
  if (!isValidEmail(email)) {
    throw new Error("A valid email is required.");
  }
  if (email.length > MAX_EMAIL_LENGTH) {
    throw new Error("Email is too long.");
  }

  const region = normalizeText(input.region);
  const serviceType = normalizeText(input.serviceType);
  const rating = normalizeText(input.rating);
  if ([region, serviceType, rating].some((value) => value.length > MAX_FILTER_LENGTH)) {
    throw new Error("A selected filter is too long.");
  }

  const opportunity = normalizeText(input.opportunity);
  const normalized: NormalizedLeadRequest = {
    email,
    region,
    serviceType,
    rating,
    opportunity: isDirectoryOpportunity(opportunity) ? opportunity : "",
  };

  if (!normalized.opportunity && !normalized.region && !normalized.serviceType && !normalized.rating) {
    throw new Error("Choose at least one opportunity, region, service type, or rating.");
  }

  return normalized;
}
