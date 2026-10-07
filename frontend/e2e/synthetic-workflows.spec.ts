import { expect, test } from "@playwright/test";

const ownerEmail = process.env.CAREGIST_SYNTHETIC_OWNER_EMAIL;
const ownerPassword = process.env.CAREGIST_SYNTHETIC_OWNER_PASSWORD;
const adminKey = process.env.API_MASTER_KEY;

test("synthetic directory filters, pagination, profile return, and provider compare use persisted fixtures", async ({ page }) => {
  await page.goto("/search?region=London");
  await expect(page.getByRole("heading", { name: "30 providers" })).toBeVisible();
  await expect(page.getByText("Page 1 of 2", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "2", exact: true }).click();
  await expect(page).toHaveURL(/region=London&page=2/);
  await expect(page.getByText("Page 2 of 2", { exact: true })).toBeVisible();
  const back = page.getByRole("link", { name: "View provider details", exact: true }).first();
  await back.click();
  await expect(page.getByRole("link", { name: "Back to search", exact: true })).toHaveAttribute(
    "href",
    "/search?region=London&page=2",
  );
  const evidenceLink = page.getByRole("link", { name: "View CQC record and reports", exact: true });
  expect(new URL((await evidenceLink.getAttribute("href"))!).hostname).toBe("www.cqc.org.uk");
  await page.getByRole("link", { name: "Back to search", exact: true }).click();

  await page.getByRole("button", { name: "Add to comparison" }).nth(0).click();
  await page.getByRole("button", { name: "Add to comparison" }).nth(1).click();
  const compare = page.getByRole("link", { name: "Compare Now" });
  await expect(compare).toBeVisible();
  await compare.click();
  await expect(page.getByRole("heading", { name: "Compare Providers" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Synthetic Workflow Care 25" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Synthetic Workflow Care 27" })).toBeVisible();
  await expect(page.getByText("Overall", { exact: true })).toBeVisible();
});

test("directory filters preserve the selected region, segment, and service in the result URL", async ({ page }) => {
  await page.goto("/search");
  await page.getByLabel("Factual segment", { exact: true }).selectOption("inadequate");
  await page.getByLabel("Region", { exact: true }).selectOption("London");
  await page.getByLabel("Service type", { exact: true }).selectOption({ label: "Home Care" });
  await page.getByRole("button", { name: "Update search", exact: true }).click();
  await expect(page).toHaveURL(/opportunity=inadequate/);
  await expect(page).toHaveURL(/region=London/);
  await expect(page).toHaveURL(/service_type=/);
  await expect(page.getByLabel("Factual segment", { exact: true })).toHaveValue("inadequate");
  await expect(page.getByLabel("Region", { exact: true })).toHaveValue("London");
});

test("find-care displays the actual local spatial-search result or a visible fail-closed error", async ({ page }) => {
  await page.goto("/find-care");
  await page.getByLabel("Postcode", { exact: true }).fill("SW1A 1AA");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  const resultOrFailure = page.getByText(/Synthetic Workflow Care 01|Search failed\.|Showing \d+ of \d+ providers/).first();
  await expect(resultOrFailure).toBeVisible();
  const resultText = await resultOrFailure.textContent();
  if (resultText?.includes("Search failed.")) {
    expect(process.env.CAREGIST_SYNTHETIC_POSTGIS_AVAILABLE).not.toBe("1");
    await expect(page.getByText("Try another postcode or a smaller radius.", { exact: false })).toHaveCount(0);
  } else {
    expect(process.env.CAREGIST_SYNTHETIC_POSTGIS_AVAILABLE).toBe("1");
    await expect(page.getByText(/Showing \d+ of \d+ providers within 5 miles of SW1A 1AA\./)).toBeVisible();
    await expect(page.getByRole("link", { name: /Synthetic Workflow Care 01/ })).toBeVisible();
  }
});

test("stale territory coverage is explained, export is scoped, and checkout stays closed", async ({ page, request }) => {
  await page.goto("/pricing/territory");
  await page.locator("#territory-region").selectOption("North West");
  await page.locator("#territory-buyer").selectOption("inadequate");
  await page.locator("#territory-service").selectOption("Homecare Agencies");
  await page.getByRole("button", { name: "Check this territory", exact: true }).click();

  await expect(page.getByTestId("territory-stale-warning")).toContainText("more than three years old");
  await expect(page.getByText("2020-02-01", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Continue to payment/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Email this scope for review" })).toBeVisible();

  await page.goto("/pricing");
  await expect(page.getByText("Online ordering is not available.", { exact: false }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /checkout|pay now|buy now/i })).toHaveCount(0);
  const invalidExport = await request.get("/api/export?token=synthetic-invalid-token");
  expect(invalidExport.status()).toBe(401);
  expect(await invalidExport.json()).toMatchObject({ error: "Export token is invalid, expired, refunded, or exhausted." });
  const entitledExport = await request.get("/api/export?token=synthetic-export-entitled-token");
  expect(entitledExport.status()).toBe(200);
  expect(entitledExport.headers()["content-type"]).toContain("text/csv");
  expect(entitledExport.headers()["content-disposition"]).toContain("attachment;");
  const csv = await entitledExport.text();
  expect(csv).toContain("Synthetic Workflow Care 01");
  expect(csv).not.toContain("Synthetic Workflow Care 31");
  const outsideScope = await request.get(
    "/api/export?token=synthetic-export-entitled-token&region=North%20West",
  );
  expect(outsideScope.status()).toBe(403);
  const checkout = await request.post("/api/v1/billing/territory-brief-checkout", {
    data: {
      email: "synthetic-buyer@example.com",
      scope_kind: "region",
      scope_name: "North West",
    },
  });
  expect(checkout.status()).toBe(503);
});

test("signup persists an unverified synthetic account and does not send mail", async ({ page }) => {
  await page.goto("/signup?plan=free");
  await page.getByLabel("Name", { exact: true }).fill("Synthetic Browser Signup");
  await page.getByLabel("Email", { exact: true }).fill("browser-signup@example.com");
  await page.getByLabel("Password", { exact: true }).fill("Synthetic-Signup-2026!");
  await page.getByRole("button", { name: "Create evaluation account", exact: true }).click();
  await expect(page).toHaveURL(/\/verify-email\?email=browser-signup%40example\.com/);
  await expect(page.getByText(/could not send a verification email/i)).toBeVisible();
});

test("password reset does not claim email delivery when the provider is unavailable", async ({ page }) => {
  await page.goto("/forgot-password");
  await expect(page.getByText(/if it is registered and email delivery is available/i)).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill("unknown-reset@example.com");
  await page.getByRole("button", { name: "Send Reset Code", exact: true }).click();
  await expect(page.getByText(/if your email is registered and email delivery is available/i)).toBeVisible();
  await expect(page.getByLabel("6-digit code", { exact: true })).toBeVisible();
});

test("login as a synthetic workspace owner, create a CRM task, and browse the manager report", async ({ page }) => {
  if (!ownerEmail || !ownerPassword) throw new Error("Synthetic local owner credentials were not provided.");
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(ownerEmail);
  await page.getByLabel("Password", { exact: true }).fill(ownerPassword);
  await page.getByRole("button", { name: "Log In", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.goto("/crm");
  await expect(page.getByRole("heading", { name: "CareGist CRM" })).toBeVisible();
  await expect(page.getByText("Synthetic Workflow Care 01").first()).toBeVisible();
  await page.getByRole("combobox", { name: "Task type" }).selectOption("follow_up");
  await page.getByRole("textbox", { name: "Task title" }).fill("Synthetic browser workflow follow-up");
  const due = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const localDue = new Date(due.getTime() - due.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
  await page.getByLabel("Due date and time").fill(localDue);
  await page.getByRole("combobox", { name: "Task priority" }).selectOption("high");
  const taskResponsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && /\/api\/v1\/crm\/contacts\/[^/]+\/tasks$/.test(response.url()),
  );
  await page.getByRole("button", { name: "Schedule task", exact: true }).click();
  const taskResponse = await taskResponsePromise;
  expect(taskResponse.status()).toBe(201);
  expect(await taskResponse.json()).toMatchObject({ title: "Synthetic browser workflow follow-up", task_type: "follow_up" });
  await expect(page.getByRole("status").filter({ hasText: "task scheduled" })).toBeVisible();
  await expect(page.getByText("Synthetic browser workflow follow-up").first()).toBeVisible();

  await page.getByRole("button", { name: "Reports", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Team performance" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Disposition report" })).toBeVisible();
});

test("admin UI uses the loopback-only master key and loads real pending-work queues", async ({ page }) => {
  if (!adminKey) throw new Error("Synthetic local admin key was not provided.");
  page.on("pageerror", (error) => console.log(`[synthetic admin page error] ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && message.text().includes("admin error boundary")) {
      console.log(`[synthetic admin boundary] ${message.text()}`);
    }
  });
  page.on("response", async (response) => {
    if (response.url().includes("/api/v1/admin/")) {
      console.log(`[synthetic admin API] ${response.status()} ${response.url()} ${await response.text().catch(() => "<unreadable>")}`);
    }
  });
  await page.goto("/admin");
  await page.getByLabel("Master API Key", { exact: true }).fill("invalid-synthetic-key");
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByText("Invalid admin key.", { exact: true })).toBeVisible();

  await page.getByLabel("Master API Key", { exact: true }).fill(adminKey);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Admin Dashboard" })).toBeVisible();
  await page.getByRole("button", { name: "Claims", exact: true }).click();
  await expect(page.getByText(/Synthetic Claimant/)).toBeVisible();
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByText("No pending claims.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Reviews", exact: true }).click();
  await expect(page.getByText(/Synthetic Reviewer/)).toBeVisible();
  await page.getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByText("No pending reviews.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Enquiries", exact: true }).click();
  await expect(page.getByText(/Synthetic Enquirer/)).toBeVisible();
  await page.getByRole("button", { name: "Mark Read", exact: true }).click();
  await expect(page.getByText("No new enquiries.", { exact: true })).toBeVisible();
});

test("non-sale API-interest workflow records only synthetic input and reports no payment", async ({ page }) => {
  await page.goto("/intelligence-feed");
  await expect(page.getByText("Not for sale · roadmap only", { exact: true })).toBeVisible();
  await page.getByLabel("Company", { exact: true }).fill("Synthetic Workflow Ltd");
  await page.getByLabel("Your name", { exact: true }).fill("Synthetic Operator");
  await page.getByLabel("Email", { exact: true }).fill("api-interest@example.com");
  await page.getByLabel("Use case", { exact: true }).fill("Synthetic integration workflow test only.");
  await page.getByRole("button", { name: "Submit pilot enquiry", exact: true }).click();
  await expect(page.getByText("Pilot enquiry received", { exact: true })).toBeVisible();
  await expect(page.getByText(/This product is not for sale/i)).toBeVisible();
});

test("retired filtered lead exports and gated payment success do not masquerade as fulfillment", async ({ page, request }) => {
  const leadResponse = await request.post("/api/leads/request", { data: {} });
  expect(leadResponse.status()).toBe(410);
  await expect(page.goto("/lead-list")).resolves.toBeTruthy();
  await expect(page).toHaveURL(/\/pricing$/);

  await page.goto("/territory-opportunity-brief/success?session_id=cs_synthetic_unpaid");
  await expect(page.getByRole("heading", { name: "Payment status is not confirmed", exact: true })).toBeVisible();
  await expect(page.getByText("This page does not confirm payment or delivery.", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: /Download/ })).toHaveCount(0);
});
