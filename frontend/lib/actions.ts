"use server";

import { getServerApiBase, getServerApiKey } from "@/lib/server-api-config";

async function apiPost(path: string, body: Record<string, unknown>) {
  const apiBase = getServerApiBase();
  const apiKey = getServerApiKey();
  const res = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: { "X-API-Key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { error: data.detail || `Request failed (${res.status})` };
  return { data, message: data.message };
}

export async function submitClaim(
  slug: string,
  claim: {
    claimant_name: string;
    claimant_email: string;
    claimant_phone?: string;
    claimant_role: string;
    organisation_name?: string;
    proof_of_association: string;
    fast_track?: boolean;
  },
) {
  return apiPost(`/api/v1/providers/${encodeURIComponent(slug)}/claim`, claim);
}

export async function submitReview(
  slug: string,
  review: {
    rating: number;
    title: string;
    body: string;
    reviewer_name: string;
    reviewer_email: string;
    relationship?: string;
    visit_date?: string;
  },
) {
  return apiPost(`/api/v1/providers/${encodeURIComponent(slug)}/reviews`, review);
}

export async function submitEnquiry(
  slug: string,
  enquiry: {
    enquirer_name: string;
    enquirer_email: string;
    enquirer_phone?: string;
    relationship?: string;
    care_type?: string;
    urgency?: string;
    message: string;
  },
) {
  return apiPost(`/api/v1/providers/${encodeURIComponent(slug)}/enquire`, enquiry);
}

export async function submitSubscribe(email: string, source: string, postcode?: string) {
  return apiPost("/api/v1/subscribe", { email, source, postcode: postcode || null });
}

export async function toggleMonitor(slug: string) {
  return apiPost(`/api/v1/providers/${encodeURIComponent(slug)}/monitor`, {});
}

export async function saveComparison(slugs: string[]) {
  return apiPost("/api/v1/comparisons", { slug_list: slugs });
}

export async function submitApiApplication(data: {
  company_name: string;
  contact_name: string;
  contact_email: string;
  use_case: string;
  expected_volume?: string;
}) {
  return apiPost("/api/v1/api-applications", data);
}
