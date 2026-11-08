import Link from "next/link";

export type Crumb = { name: string; href: string };

/** Visible breadcrumb trail. The last item is the current page. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="text-sm text-ink-soft">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={item.href} className="flex min-w-0 items-center gap-2">
              {last ? (
                <span aria-current="page" className="font-semibold text-ink break-words">
                  {item.name}
                </span>
              ) : (
                <>
                  <Link href={item.href} className="underline-offset-4 hover:underline">
                    {item.name}
                  </Link>
                  <span aria-hidden="true">›</span>
                </>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
