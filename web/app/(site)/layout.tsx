import Script from "next/script";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteHeader } from "@/components/site/SiteHeader";
import { getSiteConfig } from "@/lib/public";

// Every public page is regenerated at most every 5 minutes (ISR). This also replaces the empty
// pages built without an API, and picks up changes from admin → Settings → Keys and connections.
export const revalidate = 300;

export default async function SiteLayout({ children }: { children: React.ReactNode }) {
  const config = await getSiteConfig();
  return (
    <div className="site flex min-h-dvh flex-col bg-cream">
      <SiteHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <SiteFooter config={config} />
      {config.umami_url && config.umami_website_id && (
        <Script src={`${config.umami_url}/script.js`} data-website-id={config.umami_website_id} strategy="afterInteractive" />
      )}
    </div>
  );
}
