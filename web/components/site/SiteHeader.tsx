import Image from "next/image";
import Link from "next/link";

const NAV = [
  { href: "/books", label: "Books" },
  { href: "/free-printables", label: "Free printables" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

const linkClass = "rounded-full px-3 py-2 font-semibold text-ink hover:bg-sun-soft";

/** Top bar. On small screens the menu is a <details> disclosure, so it works without JavaScript. */
export function SiteHeader() {
  return (
    <header className="border-b border-ink/10 bg-cream">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 rounded-full pr-2">
          <Image src="/brand/lark.svg" alt="" width={44} height={44} priority />
          <span className="font-display text-2xl font-bold tracking-tight">Crayonlark</span>
        </Link>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {NAV.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className={linkClass}>
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <details className="relative md:hidden">
          <summary className="cursor-pointer list-none rounded-full border-2 border-ink px-4 py-1.5 font-semibold [&::-webkit-details-marker]:hidden">
            Menu
          </summary>
          <nav aria-label="Main" className="absolute right-0 z-40 mt-2 w-56 rounded-2xl border border-ink/10 bg-white p-2 shadow-lg">
            <ul className="flex flex-col">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className={`block ${linkClass}`}>
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </details>
      </div>
    </header>
  );
}
