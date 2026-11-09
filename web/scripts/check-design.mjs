// Design rules from CLAUDE.md, checked on every `pnpm lint`:
// 1. Corner radius at most 8px everywhere (site and admin): rounded-lg is the largest allowed.
// 2. Public site colours follow 60/30/10: cream/white base, sun secondary, coral accent, ink text.
//    No other hues on the site (the admin has its own zinc/shadcn palette).
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const walk = (dir) =>
  readdirSync(join(ROOT, dir)).flatMap((name) => {
    const rel = join(dir, name);
    return statSync(join(ROOT, rel)).isDirectory() ? walk(rel) : /\.(tsx?|css)$/.test(name) ? [rel] : [];
  });

const files = [...walk("app"), ...walk("components"), ...walk("lib")];
const isSite = (f) => f.includes("(site)") || f.startsWith("components/site") || f === "lib/content.ts";

const RADIUS = /\brounded(?:-(?:[tblrse]|tl|tr|bl|br|ss|se|es|ee))?-(?:xl|2xl|3xl|4xl|full)\b/;
const RADIUS_ARBITRARY = /\brounded(?:-[a-z]{1,2})?-\[(\d*\.?\d+)(px|rem)\]/;
const OFF_PALETTE =
  /\b(?:bg|text|ring|border|from|via|to|fill|stroke|outline|decoration|shadow|divide|accent|caret)-(?:sky|leaf|blue|green|red|emerald|rose|amber|indigo|purple|pink|teal|cyan|lime|orange|violet|fuchsia|yellow|slate|gray|zinc|neutral|stone)-\d{2,3}\b/;
// brand hexes allowed in site SVGs: ink, cream/white, sun, coral
const SITE_HEX = new Set(["1f2430", "ffffff", "fffcf7", "fff8e1", "fff0bf", "ffd45c", "ffe1d9", "ff8a72", "f4705a", "c9412c"]);

const problems = [];
for (const f of files) {
  readFileSync(join(ROOT, f), "utf8")
    .split("\n")
    .forEach((line, i) => {
      const at = `${f}:${i + 1}`;
      const r = line.match(RADIUS);
      if (r) problems.push(`${at}  ${r[0]}: corner radius must be ≤ 8px (use rounded-lg or smaller)`);
      const a = line.match(RADIUS_ARBITRARY);
      if (a && (a[2] === "rem" ? Number(a[1]) * 16 : Number(a[1])) > 8) problems.push(`${at}  ${a[0]}: corner radius must be ≤ 8px`);
      if (!isSite(f)) return;
      const c = line.match(OFF_PALETTE);
      if (c) problems.push(`${at}  ${c[0]}: site colours are cream/white (60) · sun (30) · coral (10) · ink text`);
      for (const h of line.matchAll(/#([0-9a-fA-F]{6})\b/g))
        if (!SITE_HEX.has(h[1].toLowerCase())) problems.push(`${at}  #${h[1]}: not a brand colour (60/30/10 rule)`);
    });
}

if (problems.length) {
  console.error(`Design rules (CLAUDE.md) broken in ${problems.length} place(s):\n` + problems.join("\n"));
  process.exit(1);
}
console.log("design rules ok: radius ≤ 8px, site palette 60/30/10");
