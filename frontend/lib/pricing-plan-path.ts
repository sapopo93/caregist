const PLAN_SLUGS = new Set([
  "free",
  "alerts-pro",
  "data-starter",
  "data-pro",
  "data-business",
  "enterprise",
]);

export function normalizePricingPlanSlug(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase().replace(/\s+/g, "-");
  return PLAN_SLUGS.has(normalized) ? normalized : null;
}

export function pricingPlanCardId(value: string | null | undefined): string | null {
  const plan = normalizePricingPlanSlug(value);
  return plan ? `plan-${plan}` : null;
}

