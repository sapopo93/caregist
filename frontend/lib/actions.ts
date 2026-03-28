"use server";

const API_BASE = process.env.API_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "dev_key_change_me";

async function apiPost(path: string, body: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY, "Content-Type": "application/json" },
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
