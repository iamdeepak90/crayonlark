import { LarkMark } from "./Logo";

/** Friendly placeholder for when there is nothing to show yet (or the API is taking a nap). */
export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-line bg-white px-6 py-12 text-center">
      <LarkMark className="h-12 w-12" />
      <p className="font-display text-xl font-semibold">{title}</p>
      {children && <div className="max-w-md text-muted">{children}</div>}
    </div>
  );
}
