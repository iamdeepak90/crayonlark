import type { Metadata } from "next";
import { IBM_Plex_Serif, Plus_Jakarta_Sans } from "next/font/google";
import { SITE_URL } from "@/lib/public";
import "./globals.css";

// next/font downloads these at build time and self-hosts them (no runtime Google requests).
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"], variable: "--font-jakarta" });
const plex = IBM_Plex_Serif({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-plex" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL), // PUBLIC_SITE_URL (falls back to NEXT_PUBLIC_SITE_URL, then localhost)
  title: { default: "Crayonlark – Coloring & Activity Books for Kids", template: "%s · Crayonlark" },
  description:
    "Crayonlark makes coloring and activity books for kids ages 2–10. Paperbacks on Amazon, instant printables on Etsy, and free coloring pages.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${jakarta.variable} ${plex.variable}`} suppressHydrationWarning>
      <body className="min-h-dvh bg-cream font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
