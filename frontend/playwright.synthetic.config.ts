import { defineConfig } from "@playwright/test";

const baseURL = process.env.CAREGIST_SYNTHETIC_BASE_URL;
if (!baseURL || !/^http:\/\/127\.0\.0\.1:\d+$/.test(baseURL)) {
  throw new Error("Synthetic E2E requires CAREGIST_SYNTHETIC_BASE_URL on 127.0.0.1.");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "synthetic-workflows.spec.ts",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [["line"]],
  use: {
    baseURL,
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : process.platform === "darwin"
        ? { executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" }
        : undefined,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
