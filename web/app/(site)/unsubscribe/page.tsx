import { ButtonLink } from "@/components/site/ButtonLink";
import { EmptyState } from "@/components/site/EmptyState";
import { UnsubscribeButton } from "@/components/site/UnsubscribeButton";

export const metadata = { title: "Unsubscribe", robots: { index: false, follow: false } };

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

export default async function UnsubscribePage({ searchParams }: { searchParams: SearchParams }) {
  const { token } = await searchParams;
  const valid = typeof token === "string" && token.length > 0;

  return (
    <div className="mx-auto max-w-2xl px-5 py-20">
      <h1 className="font-display text-4xl font-semibold tracking-tight">Unsubscribe</h1>
      {valid ? (
        <div className="mt-6 space-y-6">
          <p className="text-lg text-muted">Sorry to see you go! Click below and we&apos;ll stop emailing you.</p>
          <UnsubscribeButton token={token} />
        </div>
      ) : (
        <div className="mt-6">
          <EmptyState title="This unsubscribe link is missing its code.">
            <p>Please use the link at the bottom of one of our emails, or write to us and we&apos;ll remove you.</p>
            <div className="mt-5">
              <ButtonLink href="/contact">Contact us</ButtonLink>
            </div>
          </EmptyState>
        </div>
      )}
    </div>
  );
}
