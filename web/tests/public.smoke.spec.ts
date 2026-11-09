import { expect, test } from "@playwright/test";

// These run with or without the API: every page must render (empty states when the API is down).
const PAGES: { path: string; heading: RegExp }[] = [
  { path: "/", heading: /Little books for big imaginations/ },
  { path: "/books", heading: /Coloring & activity books/ },
  { path: "/books?age=4&theme=ocean-animals", heading: /Coloring & activity books/ },
  { path: "/free-printables", heading: /free (printable )?coloring pages/i },
  { path: "/free-printables/confirm?token=not-a-real-token", heading: /didn.t work/ },
  { path: "/unsubscribe", heading: /Unsubscribe/ },
  { path: "/unsubscribe?token=abc", heading: /Unsubscribe/ },
  { path: "/blog", heading: /blog/i },
  { path: "/themes", heading: /favourite/ },
  { path: "/faq", heading: /Frequently asked questions/ },
  { path: "/parents-and-teachers", heading: /grow with your kids/ },
  { path: "/how-we-make-our-books", heading: /How we make our books/ },
  { path: "/about", heading: /About Crayonlark/ },
  { path: "/contact", heading: /Say hello/ },
  { path: "/privacy", heading: /Privacy policy/ },
  { path: "/terms", heading: /Terms of use/ },
  { path: "/license", heading: /Printable license/ },
];

for (const { path, heading } of PAGES) {
  test(`page ${path} renders`, async ({ page }) => {
    const res = await page.goto(path);
    expect(res?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page).toHaveTitle(/Crayonlark/);
    await expect(page.getByRole("contentinfo")).toContainText("Designed by Crayonlark");
  });
}

test("home has canonical, Open Graph and JSON-LD", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /^https?:\/\/[^/]+\/?$/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/og\.png$/);
  const ld = await page.locator('script[type="application/ld+json"]').first().textContent();
  expect(ld).toContain('"Organization"');
});

test("default share image is served and used by inner pages", async ({ page, request }) => {
  const img = await request.get("/og.png");
  expect(img.ok()).toBeTruthy();
  expect(img.headers()["content-type"]).toContain("image/png");
  await page.goto("/about");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/about$/);
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", /\/og\.png$/);
});

test("unknown book is a 404", async ({ request }) => {
  const res = await request.get("/books/this-book-does-not-exist");
  expect(res.status()).toBe(404);
});

test("legal pages carry the hidden template note", async ({ request }) => {
  const html = await (await request.get("/privacy")).text();
  expect(html).toContain("<!-- Template — review before launch -->");
});

test("forms have a hidden honeypot", async ({ page }) => {
  await page.goto("/contact");
  await expect(page.getByLabel("Your name")).toBeVisible();
  for (const hp of await page.locator('input[name="website"]').all()) await expect(hp).not.toBeInViewport();
  await page.goto("/free-printables");
  await expect(page.getByLabel("Your email address", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Email address for free pages")).toBeAttached(); // footer sign-up
  for (const hp of await page.locator('input[name="website"]').all()) await expect(hp).not.toBeInViewport();
});

test("admin is not served on the public host", async ({ request }) => {
  const res = await request.get("/admin");
  expect(res.status()).toBe(404);
});

test("health endpoint", async ({ request }) => {
  const res = await request.get("/healthz");
  expect(res.ok()).toBeTruthy();
});

test("sitemap.xml and robots.txt", async ({ request }) => {
  const sitemap = await request.get("/sitemap.xml");
  expect(sitemap.ok()).toBeTruthy();
  expect(await sitemap.text()).toContain("/free-printables</loc>");
  const robots = await request.get("/robots.txt");
  expect(robots.ok()).toBeTruthy();
  const text = await robots.text();
  expect(text).toContain("Disallow: /api/");
  expect(text).toContain("Sitemap:");
});

test("revalidate needs the secret", async ({ request }) => {
  expect((await request.post("/revalidate")).status()).toBe(401);
  expect((await request.post("/revalidate", { headers: { "x-revalidate-secret": "wrong" } })).status()).toBe(401);
});

test("no horizontal scroll at 390px", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile only");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/books", "/free-printables", "/contact", "/privacy"]) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `horizontal overflow on ${path}`).toBeLessThanOrEqual(0);
  }
});
