import type { Metadata } from "next";
import { Fredoka, Nunito } from "next/font/google";
import "./globals.css";

// next/font downloads these at build time and self-hosts them (no runtime Google requests).
const fredoka = Fredoka({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-fredoka" });
const nunito = Nunito({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-nunito" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: { default: "Crayonlark — Little books for big imaginations", template: "%s · Crayonlark" },
  description: "Coloring and activity books for kids, in paperback and printable PDF.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${fredoka.variable} ${nunito.variable}`}>
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
