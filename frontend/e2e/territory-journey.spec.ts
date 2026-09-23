import { test, expect } from "@playwright/test";

test("public scope references have no read endpoint", async ({ request }) => {
  const response = await request.get("/api/territory/requests?reference=TSR-NOT-A-LOOKUP");
  expect(response.status()).toBe(405);
  expect(await response.text()).not.toContain("buyer@example.com");
});

test("coverage enquiry clears obsolete selections and recovers from errors", async ({ page }) => {
  let fail = false;
  await page.route("**/api/territory/coverage", async (route) => {
    const scope = route.request().postDataJSON();
    await route.fulfill({ status: fail ? 503 : 200, json: fail ? { error: "Coverage unavailable. Try again." } : {
      scope, price: { currency: "GBP", amount: 745 },
      coverage: { verdict: "ready", locationCount: 52, providerOrganisationCount: 40, mostRecentObservation: "2026-09-01", coverageSufficient: true, checkoutEligible: false, stale: false },
    } });
  });
  await page.route("**/api/territory/requests", async (route) => {
    await route.fulfill({
      status: 201,
      json: { reference: "TSR-TEST00000001", status: "requested", checkoutEligible: false },
    });
  });
  await page.goto("/pricing");
  await page.getByRole("link", { name: "Check territory coverage" }).click();
  await expect(page.getByRole("heading", { name: "See how many organisations match your scope" })).toBeVisible();
  const check = page.getByRole("button", { name: "Check this territory" });
  await expect(check).toBeDisabled();
  await page.locator("#territory-region").selectOption({ index: 1 });
  await page.locator("#territory-buyer").selectOption({ index: 1 });
  await page.locator("#territory-service").selectOption({ index: 1 });
  await check.click();
  const requestReview = page.getByRole("button", { name: "Request a scope review" });
  await expect(requestReview).toBeVisible();
  await page.locator("#territory-contact-email").fill("buyer@example.com");
  await requestReview.click();
  await expect(page.getByText("TSR-TEST00000001")).toBeVisible();
  await expect(page.getByRole("link", { name: /Continue to payment/ })).toHaveCount(0);
  await page.locator("#territory-region").selectOption({ index: 2 });
  await expect(page.getByText("TSR-TEST00000001")).toHaveCount(0);
  fail = true;
  await check.click();
  await expect(page.getByRole("alert").filter({ hasText: "Coverage unavailable" })).toContainText("Coverage unavailable");
  fail = false;
  await check.click();
  await expect(requestReview).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("an old response cannot restore coverage after selection changes", async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/territory/coverage", async (route) => {
    const scope = route.request().postDataJSON();
    await pending;
    await route.fulfill({ json: { scope, coverage: { verdict: "ready", locationCount: 52, providerOrganisationCount: 40, coverageSufficient: true, checkoutEligible: false } } });
  });
  await page.goto("/pricing/territory");
  await page.locator("#territory-region").selectOption({ index: 1 });
  await page.locator("#territory-buyer").selectOption({ index: 1 });
  const request = page.waitForRequest("**/api/territory/coverage");
  await page.getByRole("button", { name: "Check this territory" }).click();
  await request;
  await page.locator("#territory-buyer").selectOption({ index: 2 });
  const response = page.waitForResponse("**/api/territory/coverage");
  release();
  await response;
  await expect(page.getByRole("button", { name: "Request a scope review" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Check this territory" })).toBeEnabled();
});

test("checkout return page does not treat a supplied session ID as payment proof", async ({ page }) => {
  await page.goto("/territory-opportunity-brief/success?session_id=cs_unverified");
  await expect(page.getByRole("heading", { name: "Check your email for your Territory Brief" })).toBeVisible();
  await expect(page.getByText("This page does not confirm payment or delivery.", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: /Download/ })).toHaveCount(0);
});
