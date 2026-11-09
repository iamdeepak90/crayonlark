import Link from "next/link";
import { Logo } from "./Logo";

const NAV = [
  { href: "/books", label: "Books" },
  { href: "/free-printables", label: "Free printables" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
];

const MORE = [
  { href: "/themes", label: "Themes" },
  { href: "/parents-and-teachers", label: "Parents & teachers" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
];

/** Sticky top bar. On small screens the menu is a <details> disclosure, so it works without JavaScript. */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-cream/85 backdrop-blur">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to content
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Logo />

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-8 text-[15px] font-medium text-muted">
            {NAV.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="transition hover:text-ink">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <Link href="/books" className="hidden rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-ink/85 sm:inline-block">
            Shop books
          </Link>
          <details className="relative md:hidden">
            <summary className="flex h-10 w-10 cursor-pointer list-none items-center justify-center rounded-full hover:bg-line/60" aria-label="Open menu">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </summary>
            <nav aria-label="Main" className="absolute right-0 mt-2 w-56 rounded-2xl border border-line bg-white p-2 text-sm font-medium shadow-lift">
              <ul>
                {[...NAV, ...MORE].map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className="block rounded-xl px-3 py-2.5 hover:bg-cream">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </details>
        </div>
      </div>
    </header>
  );
}
