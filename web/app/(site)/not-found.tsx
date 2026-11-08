import { ButtonLink } from "@/components/site/ButtonLink";
import { EmptyState } from "@/components/site/EmptyState";

export default function SiteNotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <h1 className="mb-6 text-center text-4xl font-bold">Page not found</h1>
      <EmptyState title="This page flew away.">
        <p>It may have moved, or the book isn&apos;t on our shelf any more.</p>
        <div className="mt-5">
          <ButtonLink href="/books">Browse all books</ButtonLink>
        </div>
      </EmptyState>
    </div>
  );
}
