import { expect, test } from "@playwright/test";

test("admin login page renders and is not indexed", async ({ page }) => {
  const res = await page.goto("/login");
  expect(res?.headers()["x-robots-tag"]).toContain("noindex");
  await expect(page.getByRole("heading", { name: "Crayonlark Admin" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
});
