import Image from "next/image";

/** Friendly placeholder for when there is nothing to show yet (or the API is taking a nap). */
export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-[var(--radius-blob)] border-2 border-dashed border-ink/15 bg-white px-6 py-10 text-center">
      <Image src="/brand/lark.svg" alt="" width={64} height={64} />
      <p className="font-display text-xl font-semibold">{title}</p>
      {children && <div className="max-w-md text-ink-soft">{children}</div>}
    </div>
  );
}
