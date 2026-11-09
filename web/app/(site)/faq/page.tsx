import Link from "next/link";
import { FaqList, faqJsonLd } from "@/components/site/FaqList";
import { JsonLd } from "@/components/site/JsonLd";
import { PageHeader } from "@/components/site/PageHeader";
import { FAQ } from "@/lib/content";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Frequently asked questions",
  description: "Answers about Crayonlark coloring books and printables: where to buy, ages, paper sizes, classroom use and how the pages are made.",
  path: "/faq",
});

export default function FaqPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-14 sm:py-20">
      <JsonLd data={faqJsonLd(FAQ)} />
      <PageHeader eyebrow="Help" title="Frequently asked questions" intro="Quick answers about our books and printables." />
      <div className="mt-10">
        <FaqList items={FAQ} />
      </div>
      <div className="mt-12 rounded-lg bg-white p-6 ring-1 ring-line sm:p-8">
        <p className="font-display text-xl font-semibold">Still have a question?</p>
        <p className="mt-1 text-muted">
          Send us a message on the <Link href="/contact" className="font-semibold text-ink underline underline-offset-4">contact page</Link>. We usually reply
          within a couple of working days.
        </p>
      </div>
    </div>
  );
}
