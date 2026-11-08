import Link from "next/link";

const LINKS = [
  { href: "/books", label: "Books" },
  { href: "/free-printables", label: "Free printables" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
  { href: "/license", label: "Printable license" },
];

export function SiteFooter() {
  // Server env, read when the page is (re)generated. Only show the disclosure when we actually use a tag.
  const associates = Boolean(process.env.AMAZON_ASSOCIATES_TAG?.trim());
  return (
    <footer className="mt-16 border-t border-ink/10 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="font-semibold text-ink-soft underline-offset-4 hover:text-ink hover:underline">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="mt-6 space-y-1 text-sm text-ink-soft">
          <p>
            © {new Date().getFullYear()} Crayonlark. Designed by Crayonlark. Artwork is made with the help of AI tools,
            then checked and edited by a person.
          </p>
          {associates && <p>As an Amazon Associate, Crayonlark earns from qualifying purchases.</p>}
        </div>
      </div>
    </footer>
  );
}
