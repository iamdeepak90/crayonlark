import { ButtonLink } from "@/components/site/ButtonLink";
import { LarkMark } from "@/components/site/Logo";

export default function SiteNotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-5 py-24 text-center">
      <LarkMark className="h-16 w-16" />
      <p className="mt-6 text-sm font-semibold text-coral-600">404</p>
      <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight">This page flew away</h1>
      <p className="mt-3 text-muted">It may have moved, or the book isn&apos;t on our shelf any more.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <ButtonLink href="/books">Browse books</ButtonLink>
        <ButtonLink href="/" variant="outline">
          Go home
        </ButtonLink>
      </div>
    </div>
  );
}
