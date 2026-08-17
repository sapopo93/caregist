type HealthSnapshot = {
  commercialReadiness?: {
    checkoutReady?: unknown;
  };
};

export async function loadCommercialCheckoutReadiness(
  apiBase: string,
  fetchImpl: typeof fetch = fetch,
): Promise<boolean> {
  try {
    const response = await fetchImpl(`${apiBase}/api/v1/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });
    if (!response.ok) return false;

    const snapshot = (await response.json()) as HealthSnapshot;
    return snapshot.commercialReadiness?.checkoutReady === true;
  } catch {
    return false;
  }
}
