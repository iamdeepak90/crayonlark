import Image from "next/image";
import Link from "next/link";
import { PageHeader } from "@/components/site/PageHeader";
import { SubscribeForm } from "@/components/site/SubscribeForm";
import { getFreePrintable, pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Free printable coloring pages",
  description: "Get a free printable coloring pack from Crayonlark. Enter your email, confirm, and download. Print it for home or one classroom.",
  path: "/free-printables",
});

export default async function FreePrintablesPage() {
  const pack = await getFreePrintable();
  const ready = pack?.available !== false; // unknown (API down) → keep the friendly default copy

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <div className="grid items-start gap-10 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="min-w-0">
          <PageHeader
            title="Free printable coloring pages"
            intro={
              pack?.available && pack.title
                ? `Get “${pack.title}”${pack.pages ? `, ${pack.pages} pages` : ""}, free. Print it at home or for your class.`
                : "Get a free pack of coloring pages to print at home or for your class."
            }
          />
          <ol className="mt-8 space-y-2 text-lg">
            <li>
              <span className="font-display font-semibold text-coral-dark">1.</span> Enter your email below.
            </li>
            <li>
              <span className="font-display font-semibold text-coral-dark">2.</span> Click the link in the email we send you.
            </li>
            <li>
              <span className="font-display font-semibold text-coral-dark">3.</span> Download and print your pages.
            </li>
          </ol>
          {!ready && (
            <p className="mt-6 rounded-2xl bg-sun-soft px-4 py-3">
              Our next free pack is still being prepared. Sign up now and we&apos;ll send it as soon as it&apos;s ready.
            </p>
          )}
          <div className="mt-8 max-w-xl">
            <SubscribeForm />
          </div>
          <p className="mt-6 text-sm text-ink-soft">
            Free for personal and single-classroom use. See the{" "}
            <Link href="/license" className="font-semibold underline">
              printable license
            </Link>{" "}
            and our{" "}
            <Link href="/privacy" className="font-semibold underline">
              privacy policy
            </Link>
            .
          </p>
        </div>

        <div className="mx-auto w-full max-w-sm">
          {pack?.preview_url ? (
            <div className="relative aspect-[17/22] overflow-hidden rounded-[var(--radius-blob)] bg-white shadow-md ring-1 ring-ink/5">
              <Image src={pack.preview_url} alt={`Preview page from ${pack.title || "the free printable pack"}`} fill sizes="(min-width: 768px) 380px, 90vw" className="object-contain" />
            </div>
          ) : (
            <div className="flex aspect-square items-center justify-center rounded-[var(--radius-blob)] bg-sky-soft">
              <Image src="/brand/lark.svg" alt="" width={180} height={180} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
