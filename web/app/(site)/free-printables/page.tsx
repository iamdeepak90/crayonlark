import Image from "next/image";
import Link from "next/link";
import { FishDoodle } from "@/components/site/Doodles";
import { PageHeader } from "@/components/site/PageHeader";
import { SubscribeForm } from "@/components/site/SubscribeForm";
import { getFreePrintable, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Free printable coloring pages",
  description: "Get a free printable coloring pack from Crayonlark. Enter your email, confirm, and download. Print it for home or one classroom.",
  path: "/free-printables",
});

const STEPS = ["Enter your email below.", "Click the link in the email we send you.", "Download and print your pages."];

export default async function FreePrintablesPage() {
  const pack = await getFreePrintable();
  const ready = pack?.available !== false; // unknown (API down) → keep the friendly default copy

  return (
    <div className="mx-auto max-w-6xl px-5 py-14 sm:py-20">
      <div className="grid items-center gap-12 overflow-hidden rounded-[2rem] bg-sky-50 p-8 md:grid-cols-[1.3fr_1fr] md:p-14">
        <div className="min-w-0">
          <PageHeader
            eyebrow="Free download"
            title={pack?.available && pack.pages ? `${pack.pages} free coloring pages` : "Free printable coloring pages"}
            intro={
              pack?.available && pack.title
                ? `Get “${pack.title}” free. Print it at home or for your class, as often as you like.`
                : "Get a free pack of coloring pages to print at home or for your class."
            }
          />
          <ol className="mt-8 space-y-3">
            {STEPS.map((step, i) => (
              <li key={step} className="flex items-center gap-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-white text-sm font-bold ring-1 ring-line">{i + 1}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          {!ready && (
            <p className="mt-6 rounded-2xl bg-white px-4 py-3 text-sm ring-1 ring-line">
              Our free pack is still being prepared. Sign up now and we&apos;ll send it as soon as it&apos;s ready.
            </p>
          )}
          <div className="mt-8">
            <SubscribeForm />
          </div>
          <p className="mt-6 text-sm text-muted">
            Free for personal and single-classroom use. See the{" "}
            <Link href="/license" className="font-semibold text-ink underline underline-offset-4">
              printable license
            </Link>{" "}
            and our{" "}
            <Link href="/privacy" className="font-semibold text-ink underline underline-offset-4">
              privacy policy
            </Link>
            .
          </p>
        </div>
        <div className="relative mx-auto aspect-[17/22] w-full max-w-xs">
          <div className="absolute inset-0 translate-x-4 rotate-6 rounded-2xl bg-white shadow-soft" aria-hidden="true" />
          <div className="absolute inset-0 overflow-hidden rounded-2xl bg-white p-4 shadow-lift">
            {pack?.preview_url ? (
              <Image src={pack.preview_url} alt={`Preview page from ${pack.title || "the free printable pack"}`} fill sizes="(min-width: 768px) 320px, 80vw" className="object-contain p-3" />
            ) : (
              <FishDoodle />
            )}
          </div>
        </div>
      </div>

      <div className="mt-16 grid gap-6 md:grid-cols-3">
        {[
          { t: "Letter & A4", d: "Both paper sizes are included, so the pages print correctly wherever you are." },
          { t: "Coloring + activities", d: "Simple pictures with bold lines, plus a maze, a dot-to-dot and tracing." },
          { t: "Print again and again", d: "Print a copy for each child, or a fresh one when the first is finished." },
        ].map((f) => (
          <div key={f.t} className="rounded-3xl border border-line bg-white p-7">
            <h2 className="font-display text-xl font-semibold">{f.t}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{f.d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
