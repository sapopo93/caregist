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
      const url = new URL(candidate.startsWith("http") ? candidate : `https://${candidate}`);
      if (url.hostname === "caregist.co.uk" || url.hostname === "www.caregist.co.uk") {
        return "https://www.caregist.co.uk";
      }
      return url.toString().replace(/\/$/, "");
    } catch {
      continue;
    }
  }

  return "https://www.caregist.co.uk";
}
