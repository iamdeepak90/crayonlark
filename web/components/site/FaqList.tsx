import type { Faq } from "@/lib/content";

/** Accordion of questions (native <details>, works without JavaScript). */
export function FaqList({ items }: { items: Faq[] }) {
  return (
    <div className="divide-y divide-line border-y border-line">
      {items.map((f) => (
        <details key={f.q} className="group py-5">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
            {f.q}
            <span className="ml-4 text-xl leading-none text-muted transition group-open:rotate-45" aria-hidden="true">
              +
            </span>
          </summary>
          <p className="mt-3 leading-relaxed text-muted">{f.a}</p>
        </details>
      ))}
    </div>
  );
}

export function faqJsonLd(items: Faq[]) {
  return {
    "@type": "FAQPage",
    mainEntity: items.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
  };
}
