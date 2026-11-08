import { ContactForm } from "@/components/site/ContactForm";
import { PageHeader } from "@/components/site/PageHeader";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Contact",
  description: "Questions about a book, a printable or a classroom order? Send Crayonlark a message.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <PageHeader
        title="Contact us"
        intro="Questions about a book or a printable, spotted a mistake, or have an idea? Send us a message."
      />
      <div className="mt-8">
        <ContactForm />
      </div>
      <p className="mt-8 text-sm text-ink-soft">
        For orders, returns and shipping of paperbacks, please contact Amazon. For printable downloads bought on Etsy, you
        can also message us through Etsy.
      </p>
    </div>
  );
}
