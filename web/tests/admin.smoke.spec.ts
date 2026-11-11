import { expect, test, type Page } from "@playwright/test";

test("admin login page renders and is not indexed", async ({ page }) => {
  const res = await page.goto("/login");
  expect(res?.headers()["x-robots-tag"]).toContain("noindex");
  await expect(page.getByRole("heading", { name: "Crayonlark Admin" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});

// Logged-in pages need the API (a running stack). Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run them;
// otherwise (e.g. CI, where the build has no API) they are skipped. They only read pages, never approve.
// The API allows 10 logins per 15 minutes, so we sign in once and share one page across these tests.
const EMAIL = process.env.E2E_ADMIN_EMAIL;
const PASSWORD = process.env.E2E_ADMIN_PASSWORD;

test.describe("logged-in admin", () => {
  test.skip(!EMAIL || !PASSWORD, "set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run against a stack with the API");
  test.describe.configure({ mode: "serial" });

  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto("/login");
    await page.getByLabel("Email").fill(EMAIL!);
    await page.getByLabel("Password").fill(PASSWORD!);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("navigation", { name: "Admin" })).toBeVisible();
  });

  test.afterAll(async () => {
    await page?.close();
  });

  test("costs page renders", async () => {
    const res = await page.goto("/costs");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Costs");
    await expect(page.getByRole("progressbar", { name: "Budget used" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recent calls (last 100)" })).toBeVisible();
  });

  test("settings page shows AI providers and backups", async () => {
    const res = await page.goto("/settings");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { name: "AI providers & models" })).toBeVisible();
    await expect(page.getByRole("group", { name: "concept" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Save AI settings" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Backups" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Monthly API budget" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Telegram" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Run backup now" })).toBeVisible();
  });

  test("niches page has the web search option", async () => {
    await page.goto("/niches");
    await expect(page.getByLabel("Use web search")).toBeVisible();
  });

  test("sales page renders with period selector, imports and weekly report", async () => {
    const res = await page.goto("/sales?days=30");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sales");
    await expect(page.getByRole("link", { name: "30 days" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("heading", { name: "Import sales" })).toBeVisible();
    await expect(page.getByText("Upload KDP CSV")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Weekly report" })).toBeVisible();
  });

  test("today shows the two approvals and the Autopilot", async () => {
    const res = await page.goto("/");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Today");
    await expect(page.getByText("Autopilot", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "1. Approve for Etsy" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "2. Pick for KDP" }).first()).toBeVisible();
  });

  test("approval screens render", async () => {
    let res = await page.goto("/etsy");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Approve for Etsy");
    await expect(page.getByRole("heading", { name: "Etsy queue" })).toBeVisible();
    res = await page.goto("/kdp");
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Pick for KDP");
    await expect(page.getByText(/Score = sales/)).toBeVisible();
  });
});
