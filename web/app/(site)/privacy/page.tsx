import Link from "next/link";
import { TextPage } from "@/components/site/TextPage";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Privacy policy",
  description: "What Crayonlark collects (very little), why, and how to get it deleted.",
  path: "/privacy",
});

const ANALYTICS = Boolean(process.env.NEXT_PUBLIC_UMAMI_URL && process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID);
const TURNSTILE = Boolean(process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY);

export default function PrivacyPage() {
  return (
    <TextPage title="Privacy policy" intro="Short version: we collect as little as possible and never sell it." template>
      <h2>Who we are</h2>
      <p>
        Crayonlark is a small one-person studio that makes coloring and activity books. This website is for parents,
        teachers and other grown-ups. It is not meant to be used by children on their own.
      </p>

      <h2>Free printables (email sign-up)</h2>
      <p>
        When you ask for a free printable, we store your email address. We first send one email asking you to confirm
        (double opt-in). Only after you click that link do we add you to our list and give you the download.
      </p>
      <p>
        We use your email to send the printable and occasional news about new books and printables. Every email has an
        unsubscribe link, and unsubscribing takes one click. We keep your email address until you unsubscribe or ask us
        to delete it.
      </p>

      <h2>Contact messages</h2>
      <p>
        When you use the <Link href="/contact">contact form</Link>, we receive your name, email address and message. We use
        them only to reply to you, and delete them when they are no longer needed.
      </p>

      <h2>Spam protection</h2>
      <p>
        To stop spam, our server briefly uses your IP address to limit how many forms can be sent per hour. We don&apos;t
        use it for anything else.
        {TURNSTILE &&
          " The contact form also uses Cloudflare Turnstile, a privacy-friendly check that tells people and bots apart without showing ads or tracking you across sites."}
      </p>

      <h2>Analytics and cookies</h2>
      {ANALYTICS ? (
        <p>
          We use Umami, a privacy-friendly analytics tool, to count page visits (for example, which pages are popular). It
          does not use cookies, does not build a profile of you, and does not collect personal information.
        </p>
      ) : (
        <p>We don&apos;t run any analytics on this website at the moment.</p>
      )}
      <p>We don&apos;t show ads and we don&apos;t use tracking or advertising cookies.</p>

      <h2>Links to Amazon and Etsy</h2>
      <p>
        Our books are sold on Amazon and Etsy. When you follow a link to those sites, their own privacy policies apply.
        Some Amazon links may be affiliate links, which means Amazon knows you came from our site.
      </p>

      <h2>Who we share data with</h2>
      <p>
        We never sell your data. We only use the services needed to run this website and send email, and they may process
        your data for us.
      </p>

      <h2>Your rights</h2>
      <p>
        You can ask us to show, correct or delete the data we hold about you at any time. Just send a message through the{" "}
        <Link href="/contact">contact page</Link>.
      </p>

      <h2>Changes</h2>
      <p>If we change this policy, we&apos;ll update this page.</p>
    </TextPage>
  );
}
