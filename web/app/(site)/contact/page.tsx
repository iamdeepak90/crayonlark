import { ContactForm } from "@/components/site/ContactForm";
import { PageHeader } from "@/components/site/PageHeader";
import { getSiteConfig, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Contact",
  description: "Questions about a book, a printable or a classroom order? Send Crayonlark a message.",
  path: "/contact",
});

export default async function ContactPage() {
  const { turnstile_site_key } = await getSiteConfig();
  return (
    <div className="mx-auto max-w-3xl px-5 py-14 sm:py-20">
      <PageHeader
        eyebrow="Contact"
        title="Say hello"
        intro="Questions about a book or a printable, spotted a mistake, or have an idea? Send us a message."
      />
      <div className="mt-10 rounded-3xl bg-white p-6 ring-1 ring-line sm:p-10">
        <ContactForm turnstileSiteKey={turnstile_site_key} />
      </div>
      <p className="mt-8 text-sm text-muted">
        For orders, returns and shipping of paperbacks, please contact Amazon. For printable downloads bought on Etsy, you
        can also message us through Etsy.
      </p>
    </div>
  );
}
