import Script from "next/script";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import { getSiteConfig } from "@/lib/public";

// Every public page is regenerated at most every 5 minutes (ISR). This also replaces the empty
// pages built without an API, and picks up changes from admin → Settings → Integrations.
export const revalidate = 300;

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  const { umami_url: UMAMI_URL, umami_website_id: UMAMI_ID, amazon_associates_tag } = await getSiteConfig();
  return (
    <div className="flex min-h-dvh flex-col">
      <SiteHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <SiteFooter associates={Boolean(amazon_associates_tag)} />
      {UMAMI_URL && UMAMI_ID && <Script src={`${UMAMI_URL}/script.js`} data-website-id={UMAMI_ID} strategy="afterInteractive" />}
    </div>
  );
}
