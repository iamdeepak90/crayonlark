import { defineConfig, devices } from "@playwright/test";

// Smoke tests. Public pages run against http://localhost:3000, admin against http://admin.localhost:3000
// (*.localhost resolves to 127.0.0.1 in Chromium). Set BASE_URL to test a running stack instead.
const PORT = Number(process.env.PORT ?? 3100);
const base = process.env.BASE_URL ?? `http://localhost:${PORT}`;
const adminBase = process.env.ADMIN_BASE_URL ?? base.replace("://localhost", "://admin.localhost");

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: { trace: "retain-on-failure" },
  projects: [
    { name: "public", testMatch: /public\..*spec\.ts/, use: { ...devices["Desktop Chrome"], baseURL: base } },
    { name: "mobile", testMatch: /public\..*spec\.ts/, use: { ...devices["Pixel 7"], baseURL: base } },
    { name: "admin", testMatch: /admin\..*spec\.ts/, use: { ...devices["Desktop Chrome"], baseURL: adminBase } },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : { command: `pnpm start -p ${PORT}`, url: `${base}/healthz`, reuseExistingServer: !process.env.CI, timeout: 60_000 },
});
