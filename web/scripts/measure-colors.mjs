// Measures the 60/30/10 colour split of the public site (CLAUDE.md design rule).
// Run against a running site:  BASE_URL=http://localhost:3000 pnpm colors
// Counts screen pixels of full-page screenshots: base = cream/white, secondary = sun (yellow),
// accent = coral. Ink text and grey lines are neutral and left out of the split.
import { chromium } from "@playwright/test";

const BASE = process.env.BASE_URL ?? "http://localhost:3000";
const PAGES = ["/", "/books", "/themes", "/blog", "/free-printables", "/about", "/faq", "/parents-and-teachers"];

function classify(d) {
  const out = { base: 0, secondary: 0, accent: 0, other: 0 };
  for (let i = 0; i < d.length; i += 16) {
    const r = d[i] / 255, g = d[i + 1] / 255, b = d[i + 2] / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, dl = mx - mn;
    if (l < 0.3) continue; // ink text
    const s = dl === 0 ? 0 : dl / (1 - Math.abs(2 * l - 1));
    if (s < 0.25 || dl < 0.06) {
      if (l > 0.9) out.base++;
      continue; // grey text and lines
    }
    let h = mx === r ? 60 * (((g - b) / dl) % 6) : mx === g ? 60 * ((b - r) / dl + 2) : 60 * ((r - g) / dl + 4);
    if (h < 0) h += 360;
    if (h < 25 || h >= 330) out.accent++;
    else if (h < 70) out.secondary++;
    else out.other++; // illustrations and photos
  }
  return out;
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const lab = await browser.newPage(); // blank page that counts pixels, apart from the site
const totals = { base: 0, secondary: 0, accent: 0, other: 0 };
const pct = (o) => {
  const n = o.base + o.secondary + o.accent + o.other || 1;
  return `${((100 * o.base) / n).toFixed(0)} / ${((100 * o.secondary) / n).toFixed(0)} / ${((100 * o.accent) / n).toFixed(0)}`;
};
console.log("page".padEnd(24), "base / secondary / accent (%)");
for (const path of PAGES) {
  await page.goto(BASE + path, { waitUntil: "load" });
  const png = (await page.screenshot({ fullPage: true })).toString("base64");
  const o = await lab.evaluate(
    async ({ b64, src }) => {
      const img = new Image();
      img.src = "data:image/png;base64," + b64;
      await img.decode();
      const c = new OffscreenCanvas(img.width, img.height);
      const x = c.getContext("2d");
      x.drawImage(img, 0, 0);
      return new Function(`return (${src})`)()(x.getImageData(0, 0, img.width, img.height).data);
    },
    { b64: png, src: classify.toString() },
  );
  for (const k of Object.keys(totals)) totals[k] += o[k];
  console.log(path.padEnd(24), pct(o));
}
console.log("whole site".padEnd(24), pct(totals), "  target ≈ 60 / 30 / 10");
await browser.close();
