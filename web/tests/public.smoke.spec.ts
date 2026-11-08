import { expect, test } from "@playwright/test";

test("home page renders brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page).toHaveTitle(/Crayonlark/);
});

test("admin is not served on the public host", async ({ request }) => {
  const res = await request.get("/admin");
  expect(res.status()).toBe(404);
});

test("health endpoint", async ({ request }) => {
  const res = await request.get("/healthz");
  expect(res.ok()).toBeTruthy();
});
