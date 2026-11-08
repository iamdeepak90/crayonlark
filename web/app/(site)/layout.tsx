import Script from "next/script";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";

// Every public page is regenerated at most every 5 minutes (ISR). This also replaces the empty
// pages built without an API, and picks up runtime env such as AMAZON_ASSOCIATES_TAG.
export const revalidate = 300;

const UMAMI_URL = process.env.NEXT_PUBLIC_UMAMI_URL?.replace(/\/+$/, "");
const UMAMI_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID;

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <SiteFooter />
      {UMAMI_URL && UMAMI_ID && <Script src={`${UMAMI_URL}/script.js`} data-website-id={UMAMI_ID} strategy="afterInteractive" />}
    </div>
  );
}
