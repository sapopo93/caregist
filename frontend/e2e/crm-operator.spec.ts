import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const session = process.env.CAREGIST_E2E_SESSION;

test.skip(!session, "CAREGIST_E2E_SESSION must contain an isolated synthetic session.");

test("non-technical operator can navigate CRM, create a task, and review reports", async ({
  context,
  page,
}) => {
  await context.addCookies([
    {
      name: "caregist_session",
      value: session!,
      url: process.env.CAREGIST_E2E_BASE_URL || "http://127.0.0.1:3001",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  await page.goto("/crm");
  await expect(page).toHaveURL(/\/crm$/);
  await expect(page.getByRole("heading", { name: "CareGist CRM" })).toBeVisible();
  await expect(page.getByText("Acme Care (Synthetic)").first()).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.getByRole("button", { name: /Acme Care \(Synthetic\).*\+442079460123/ }).click();
  await expect(page.getByText("Pilot test number").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Call contact" })).toBeDisabled();

  const dispositionPrompt = page.getByText("What happened? Choose one before the next call.");
  if (await dispositionPrompt.isVisible()) {
    for (const name of ["No contact", "Connected", "Callback", "Do not call"]) {
      await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
    }
    await page.reload();
    await expect(dispositionPrompt).toBeVisible();
    await page.getByRole("button", { name: "No contact", exact: true }).click();
    await page.getByRole("button", { name: "No answer", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "No Answer saved" })).toBeVisible();
  }

  await page.getByRole("combobox", { name: "Task type" }).selectOption("follow_up");
  const taskTitle = `Synthetic E2E follow-up ${Date.now()}`;
  await page.getByRole("textbox", { name: "Task title" }).fill(taskTitle);
  const due = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const localDue = new Date(due.getTime() - due.getTimezoneOffset() * 60_000)
    .toISOString().slice(0, 16);
  await page.getByLabel("Due date and time").fill(localDue);
  await page.getByRole("combobox", { name: "Task priority" }).selectOption("high");
  await page.getByRole("button", { name: "Schedule task" }).click();
  await expect(page.getByRole("status").filter({ hasText: "task scheduled" })).toBeVisible();
  await expect(page.getByText(taskTitle).first()).toBeVisible();

  await page.getByRole("button", { name: "Pipeline" }).click();
  await expect(page.getByText("Synthetic pilot")).toBeVisible();

  await page.getByRole("button", { name: "Reports" }).click();
  await expect(page.getByRole("heading", { name: "Team performance" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Disposition report" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Campaign report" })).toBeVisible();

  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);

  await page.screenshot({
    path: "test-results/caregist-crm-operator-e2e.png",
    fullPage: true,
  });
});
