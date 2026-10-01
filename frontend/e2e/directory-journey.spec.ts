import { test, expect } from "@playwright/test";

test("provider details retain the search and link to official evidence", async ({ page }) => {
  await page.goto("/search?region=London&page=2");
  const details = page.getByRole("link", { name: "View provider details", exact: true }).first();
  await expect(details).toBeVisible();
  const href = (await details.getAttribute("href"))!;
  expect(decodeURIComponent(href)).toContain("returnTo=/search?region=London&page=2");
  await details.click();
  const back = page.getByRole("link", { name: "Back to search", exact: true });
  await expect(back).toHaveAttribute("href", "/search?region=London&page=2");
  const evidence = page.getByRole("link", { name: "View CQC record and reports", exact: true });
  await expect(evidence).toBeVisible();
  expect(new URL((await evidence.getAttribute("href"))!).hostname).toMatch(/(^|\.)cqc\.org\.uk$/);
  await back.click();
  await expect(page.getByLabel("Region", { exact: true })).toHaveValue("London");
  await expect(page).toHaveURL(/page=2/);
});

test("empty searches provide a clear recovery", async ({ page }) => {
  await page.goto("/search?q=caregist-no-match-regression-20261001");
  const clear = page.getByRole("link", { name: "Clear filters and start again", exact: true });
  await expect(clear).toBeVisible();
  await clear.click();
  await expect(page.getByLabel("Name or town", { exact: true })).toHaveValue("");
  await expect(page.getByRole("link", { name: "View provider details", exact: true }).first()).toBeVisible();
});
