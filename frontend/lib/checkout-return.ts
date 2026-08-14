export type CheckoutReturnStatus = {
  checkout_status?: string | null;
  payment_status?: string | null;
  entitlement_ready?: boolean;
  tier?: string | null;
};

export async function pollCheckoutReturn(
  load: () => Promise<CheckoutReturnStatus>,
  options: {
    attempts?: number;
    delayMs?: number;
    sleep?: (delayMs: number) => Promise<void>;
  } = {},
): Promise<CheckoutReturnStatus> {
  const attempts = Math.max(1, options.attempts ?? 12);
  const delayMs = Math.max(0, options.delayMs ?? 1_500);
  const sleep = options.sleep ?? ((delay) => new Promise((resolve) => setTimeout(resolve, delay)));
  let latest: CheckoutReturnStatus = {};

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    latest = await load();
    if (latest.entitlement_ready) return latest;
    if (attempt + 1 < attempts) await sleep(delayMs);
  }

  return latest;
}
