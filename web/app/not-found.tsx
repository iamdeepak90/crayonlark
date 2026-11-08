import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl px-6 py-24 text-center">
      <h1 className="text-4xl font-bold">Page not found</h1>
      <p className="mt-3 text-ink-soft">This page flew away.</p>
      <Link href="/" className="mt-6 inline-block font-semibold text-coral-dark underline">
        Back to home
      </Link>
    </main>
  );
}
