import { ButtonLink, buttonClass } from "@/components/site/ButtonLink";
import { EmptyState } from "@/components/site/EmptyState";
import { confirmSubscription } from "@/lib/public";

export const metadata = { title: "Confirm your email", robots: { index: false, follow: false } };

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

/** Landing page for the double opt-in email link. Confirms on the server, then offers the download. */
export default async function ConfirmPage({ searchParams }: { searchParams: SearchParams }) {
  const { token } = await searchParams;
  const result = typeof token === "string" && token ? await confirmSubscription(token) : null;
  const downloadUrl = result?.ok && result.download_url.startsWith("/") ? result.download_url : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-14 sm:px-6">
      {downloadUrl ? (
        <div className="text-center">
          <h1 className="text-4xl font-bold">You&apos;re in!</h1>
          <p className="mt-4 text-lg text-ink-soft">Thanks for confirming your email. Your free coloring pages are ready.</p>
          <a href={downloadUrl} className={`mt-8 ${buttonClass("primary")}`}>
            Download the printable (PDF)
          </a>
          <p className="mt-6 text-sm text-ink-soft">Tip: print on plain A4 or US Letter paper, “fit to page”.</p>
        </div>
      ) : (
        <>
          <h1 className="mb-6 text-center text-4xl font-bold">Hmm, that link didn&apos;t work</h1>
          <EmptyState title="The confirmation link is invalid or has expired.">
            <p>Links can only be used for a while. Sign up again and we&apos;ll send you a fresh one.</p>
            <div className="mt-5">
              <ButtonLink href="/free-printables">Try again</ButtonLink>
            </div>
          </EmptyState>
        </>
      )}
    </div>
  );
}
