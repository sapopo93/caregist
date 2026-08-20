import { defineConfig } from "@playwright/test";

const port = 3111;

export default defineConfig({
  testDir: "./e2e-production",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
  },
  webServer: {
    command: `npm run start -- -p ${port}`,
    url: `http://127.0.0.1:${port}`,
    env: {
      CAREGIST_BACKEND_URL:
        process.env.CAREGIST_BACKEND_URL || "http://127.0.0.1:8000",
      NEXT_TELEMETRY_DISABLED: "1",
    },
    reuseExistingServer: false,
    timeout: 60_000,
  },
  reporter: [["line"]],
});
