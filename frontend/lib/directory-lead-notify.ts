import "server-only";

import type { NormalizedLeadRequest } from "./directory-leads.ts";

interface LeadNotificationOptions {
  mode: "database" | "stateless";
  failureReason?: string;
}

function getNotificationConfig() {
  const apiKey = process.env.RESEND_API_KEY?.trim() ?? "";
  const fromEmail = process.env.ENQUIRY_FROM_EMAIL?.trim() ?? "";
  const notifyEmail = process.env.LEAD_NOTIFY_EMAIL?.trim() || "hello@caregist.co.uk";

  return {
    apiKey,
    fromEmail,
    notifyEmail,
  };
}

export function canSendLeadNotifications(): boolean {
  const { apiKey, fromEmail } = getNotificationConfig();
  return Boolean(apiKey && fromEmail);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function subjectPart(value: string): string {
  return value.replace(/[\r\n]+/g, " ").trim();
}

export async function sendLeadNotification(
  request: NormalizedLeadRequest,
  options: LeadNotificationOptions,
): Promise<boolean> {
  const { apiKey, fromEmail, notifyEmail } = getNotificationConfig();
  if (!apiKey || !fromEmail) {
    return false;
  }

  const scopeSummary =
    [
      request.opportunity || "All opportunities",
      request.region || "All regions",
      request.serviceType || "All service types",
      request.rating || "All ratings",
    ]
      .map(subjectPart)
      .join(" / ");

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: fromEmail,
      to: [notifyEmail],
      reply_to: request.email,
      subject: `CareGist lead request: ${scopeSummary}`,
      html: [
        "<h1>CareGist lead request</h1>",
        `<p><strong>Email:</strong> ${escapeHtml(request.email)}</p>`,
        `<p><strong>Region:</strong> ${escapeHtml(request.region || "All regions")}</p>`,
        `<p><strong>Service type:</strong> ${escapeHtml(request.serviceType || "All service types")}</p>`,
        `<p><strong>Rating:</strong> ${escapeHtml(request.rating || "All ratings")}</p>`,
        `<p><strong>Opportunity:</strong> ${escapeHtml(request.opportunity || "All opportunities")}</p>`,
        `<p><strong>Capture mode:</strong> ${escapeHtml(options.mode)}</p>`,
        options.failureReason
          ? `<p><strong>Primary DB failure:</strong> ${escapeHtml(options.failureReason)}</p>`
          : "",
      ].join(""),
    }),
    signal: AbortSignal.timeout(5_000),
  });

  return response.ok;
}
