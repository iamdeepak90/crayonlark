/** Page title block used at the top of simple pages. */
export function PageHeader({ title, intro }: { title: string; intro?: React.ReactNode }) {
  return (
    <div className="max-w-3xl">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{title}</h1>
      {intro && <p className="mt-4 text-lg text-ink-soft sm:text-xl">{intro}</p>}
    </div>
  );
}
