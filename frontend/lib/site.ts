export function getSiteUrl(): string {
  const candidates = [
    process.env.NEXT_PUBLIC_APP_URL,
    process.env.APP_URL,
    process.env.VERCEL_PROJECT_PRODUCTION_URL,
    process.env.VERCEL_URL,
  ];

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }

    try {
      return new URL(candidate.startsWith("http") ? candidate : `https://${candidate}`).toString().replace(/\/$/, "");
    } catch {
      continue;
    }
  }

  return "https://caregist.co.uk";
}

export function getStripePaymentLinkUrl(): string | null {
  const value = process.env.STRIPE_PAYMENT_LINK_URL?.trim();
  return value ? value : null;
}
