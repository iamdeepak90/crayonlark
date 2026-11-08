import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";

/**
 * Default social share image (/og.png), generated once at build time. Pages reference it through
 * pageMetadata() in lib/public.ts; book and post pages use their own cover instead. A plain route
 * (not the opengraph-image file convention) so the URL is stable and child pages can point to it.
 */
export const dynamic = "force-static";

const size = { width: 1200, height: 630 };

export async function GET() {
  const svg = await readFile(join(process.cwd(), "public/brand/lark.svg"));
  const lark = `data:image/svg+xml;base64,${svg.toString("base64")}`;
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          gap: 56,
          padding: "0 96px",
          background: "#FFF8EE",
          borderBottom: "24px solid #FFC93C",
          color: "#1F2333",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- ImageResponse renders plain <img> */}
        <img src={lark} width={300} height={300} alt="" />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 104, fontWeight: 700, letterSpacing: -2 }}>Crayonlark</div>
          <div style={{ fontSize: 44, color: "#4A4F63", marginTop: 12 }}>Little books for big imaginations</div>
          <div style={{ display: "flex", gap: 16, marginTop: 36 }}>
            <div style={{ background: "#5BC0EB", borderRadius: 999, padding: "10px 28px", fontSize: 30 }}>Coloring books</div>
            <div style={{ background: "#FF6F59", borderRadius: 999, padding: "10px 28px", fontSize: 30 }}>Printables</div>
          </div>
        </div>
      </div>
    ),
    size,
  );
}
