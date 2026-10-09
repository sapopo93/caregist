# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: territory-journey.spec.ts >> checkout return page does not treat a supplied session ID as payment proof
- Location: e2e/territory-journey.spec.ts:60:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Check your email for your Territory Brief' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('heading', { name: 'Check your email for your Territory Brief' })

```

```yaml
- banner:
  - link "CareGist":
    - /url: /
    - img "CareGist"
  - navigation "Primary":
    - link "Directory":
      - /url: /search
    - link "Products":
      - /url: /pricing
    - link "About":
      - /url: /why-caregist
    - link "Check your territory":
      - /url: /pricing/territory
  - navigation "Account":
    - link "Log In":
      - /url: /login
    - link "Sign Up":
      - /url: /signup
- main:
  - main:
    - heading "Payment status is not confirmed" [level=1]
    - paragraph: If Stripe confirms payment and your brief is prepared, we will email your private PDF and CSV download links to the address you used at checkout.
    - paragraph:
      - text: This page does not confirm payment or delivery. If your links do not arrive, contact
      - link "support@caregist.co.uk":
        - /url: mailto:support@caregist.co.uk
      - text: with your Stripe receipt reference. Do not pay again.
    - paragraph:
      - link "Return to the Territory Opportunity Brief":
        - /url: /territory-opportunity-brief
- dialog "Cookie choices":
  - paragraph:
    - text: We use strictly necessary storage for sign-in, security, and requested preferences. We do not use advertising cookies. Read our
    - link "cookie policy":
      - /url: /cookies
    - text: .
  - button "Continue"
- contentinfo:
  - paragraph:
    - text: Contains public sector information licensed under the
    - link "Open Government Licence v3.0":
      - /url: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
    - text: .
  - paragraph: CareGist is not an official CQC service.
  - paragraph:
    - text: If you have concerns about care quality, contact CQC directly at
    - link "cqc.org.uk/contact-us":
      - /url: https://www.cqc.org.uk/contact-us
    - text: or call 03000 616161.
  - link "Privacy Policy":
    - /url: /privacy
  - link "Terms of Service":
    - /url: /terms
  - link "Acceptable Use":
    - /url: /acceptable-use
  - link "Cookies":
    - /url: /cookies
  - link "Data Status":
    - /url: /data-status
  - link "Directory":
    - /url: /search
  - link "Find Care":
    - /url: /find-care
  - link "Pricing":
    - /url: /pricing
  - link "Why CareGist":
    - /url: /why-caregist
  - link "Contact":
    - /url: mailto:support@caregist.co.uk
- alert
```

# Test source

```ts
  1   | import { test, expect } from "@playwright/test";
  2   |
  3   | test("coverage enquiry clears obsolete selections and recovers from errors", async ({ page }) => {
  4   |   let fail = false;
  5   |   await page.route("**/api/territory/coverage", async (route) => {
  6   |     const scope = route.request().postDataJSON();
  7   |     await route.fulfill({ status: fail ? 503 : 200, json: fail ? { error: "Coverage unavailable. Try again." } : {
  8   |       scope, price: { currency: "GBP", amount: 745 },
  9   |       coverage: { verdict: "ready", providerCount: 40, mostRecentObservation: "2026-09-01", canCheckout: true, stale: false },
  10  |     } });
  11  |   });
  12  |   await page.goto("/pricing");
  13  |   await page.getByRole("region", { name: "CareGist products" }).getByRole("link", { name: "Check your territory" }).click();
  14  |   await expect(page.getByRole("heading", { name: "See how many organisations match your scope" })).toBeVisible();
  15  |   const check = page.getByRole("button", { name: "Check this territory" });
  16  |   await expect(check).toBeDisabled();
  17  |   await page.locator("#territory-region").selectOption({ index: 1 });
  18  |   await page.locator("#territory-buyer").selectOption({ index: 1 });
  19  |   await page.locator("#territory-service").selectOption({ index: 1 });
  20  |   await check.click();
  21  |   const email = page.getByRole("link", { name: "Email this scope for review" });
  22  |   await expect(email).toBeVisible();
  23  |   const href = decodeURIComponent((await email.getAttribute("href"))!);
  24  |   expect(href).toContain(await page.locator("#territory-service").inputValue());
  25  |   await expect(page.getByRole("link", { name: /Continue to payment/ })).toHaveCount(0);
  26  |   await page.locator("#territory-region").selectOption({ index: 2 });
  27  |   await expect(email).toHaveCount(0);
  28  |   fail = true;
  29  |   await check.click();
  30  |   await expect(page.getByRole("alert").filter({ hasText: "Coverage unavailable" })).toContainText("Coverage unavailable");
  31  |   fail = false;
  32  |   await check.click();
  33  |   await expect(email).toBeVisible();
  34  |   await page.setViewportSize({ width: 390, height: 844 });
  35  |   expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  36  | });
  37  |
  38  | test("an old response cannot restore coverage after selection changes", async ({ page }) => {
  39  |   let release!: () => void;
  40  |   const pending = new Promise<void>((resolve) => { release = resolve; });
  41  |   await page.route("**/api/territory/coverage", async (route) => {
  42  |     const scope = route.request().postDataJSON();
  43  |     await pending;
  44  |     await route.fulfill({ json: { scope, coverage: { verdict: "ready", providerCount: 40, canCheckout: true } } });
  45  |   });
  46  |   await page.goto("/pricing/territory");
  47  |   await page.locator("#territory-region").selectOption({ index: 1 });
  48  |   await page.locator("#territory-buyer").selectOption({ index: 1 });
  49  |   const request = page.waitForRequest("**/api/territory/coverage");
  50  |   await page.getByRole("button", { name: "Check this territory" }).click();
  51  |   await request;
  52  |   await page.locator("#territory-buyer").selectOption({ index: 2 });
  53  |   const response = page.waitForResponse("**/api/territory/coverage");
  54  |   release();
  55  |   await response;
  56  |   await expect(page.getByRole("link", { name: "Email this scope for review" })).toHaveCount(0);
  57  |   await expect(page.getByRole("button", { name: "Check this territory" })).toBeEnabled();
  58  | });
  59  |
  60  | test("checkout return page does not treat a supplied session ID as payment proof", async ({ page }) => {
  61  |   await page.goto("/territory-opportunity-brief/success?session_id=cs_unverified");
> 62  |   await expect(page.getByRole("heading", { name: "Check your email for your Territory Brief" })).toBeVisible();
      |                                                                                                  ^ Error: expect(locator).toBeVisible() failed
  63  |   await expect(page.getByText("This page does not confirm payment or delivery.", { exact: false })).toBeVisible();
  64  |   await expect(page.getByRole("link", { name: /Download/ })).toHaveCount(0);
  65  | });
  66  |
  67  | test("small territories retain free discovery and a usable webmail enquiry", async ({ page }) => {
  68  |   await page.route("**/api/territory/coverage", async (route) => {
  69  |     const scope = route.request().postDataJSON();
  70  |     await route.fulfill({ json: { scope, coverage: { verdict: "insufficient", providerCount: 7, mostRecentObservation: "2026-06-10", canCheckout: false } } });
  71  |   });
  72  |   await page.goto("/pricing/territory");
  73  |   await page.getByLabel("Region", { exact: true }).selectOption("London");
  74  |   await page.getByLabel("Which provider group do you want to research?", { exact: true }).selectOption("inadequate");
  75  |   await page.locator("#territory-service").selectOption("Homecare Agencies");
  76  |   await page.getByRole("button", { name: "Check this territory", exact: true }).click();
  77  |   const free = page.getByRole("link", { name: "View matching providers for free" });
  78  |   await expect(free).toHaveAttribute("href", "/search?region=London&opportunity=inadequate&service_type=Homecare+Agencies");
  79  |   const custom = page.getByRole("link", { name: "Ask about a custom scope" });
  80  |   await expect(custom).toBeVisible();
  81  |   expect(decodeURIComponent((await custom.getAttribute("href"))!)).toContain("This is an enquiry, not an order.");
  82  |   await page.getByText("No email app? Copy your enquiry", { exact: true }).click();
  83  |   await expect(page.getByLabel("Your scope enquiry")).toHaveValue(/Region: London[\s\S]*Providers in scope: 7/);
  84  |   await page.evaluate(() => { Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async () => { throw new Error("Denied"); } } }); });
  85  |   await page.getByRole("button", { name: "Copy enquiry", exact: true }).click();
  86  |   await expect(page.getByText("Copy is unavailable in this browser.", { exact: false })).toBeVisible();
  87  |   await page.setViewportSize({ width: 390, height: 844 });
  88  |   expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  89  |   await expect(page.getByRole("link", { name: /Continue to payment/ })).toHaveCount(0);
  90  |   await page.locator("#territory-region").selectOption("South East");
  91  |   await expect(custom).toHaveCount(0);
  92  |   await expect(free).toHaveCount(0);
  93  |   await expect(page.getByLabel("Your scope enquiry")).toHaveCount(0);
  94  | });
  95  |
  96  | test("a stalled coverage check times out and allows retry", async ({ page }) => {
  97  |   await page.clock.install();
  98  |   await page.route("**/api/territory/coverage", () => {});
  99  |   await page.goto("/pricing/territory");
  100 |   await page.locator("#territory-region").selectOption("London");
  101 |   await page.locator("#territory-buyer").selectOption("new_90");
  102 |   await page.getByRole("button", { name: "Check this territory", exact: true }).click();
  103 |   await page.clock.fastForward(16000);
  104 |   await expect(page.getByRole("alert").filter({ hasText: "coverage check failed" })).toBeVisible();
  105 |   await expect(page.getByRole("button", { name: "Check this territory", exact: true })).toBeEnabled();
  106 | });
  107 |
  108 | test("territory selectors cannot lose input before hydration", async ({ page }) => {
  109 |   let release!: () => void;
  110 |   const pending = new Promise<void>((resolve) => { release = resolve; });
  111 |   await page.route(/\/_next\/.*\.js(?:\?.*)?$/, async (route) => { await pending; await route.continue(); });
  112 |   await page.goto("/pricing/territory", { waitUntil: "commit" });
  113 |   await expect(page.locator("#territory-region")).toBeDisabled();
  114 |   await expect(page.locator("#territory-buyer")).toBeDisabled();
  115 |   release();
  116 |   await expect(page.locator("#territory-region")).toBeEnabled();
  117 |   await page.locator("#territory-region").selectOption("London");
  118 |   await page.locator("#territory-buyer").selectOption("inadequate");
  119 |   await expect(page.getByRole("button", { name: "Check this territory", exact: true })).toBeEnabled();
  120 | });
  121 |
```
