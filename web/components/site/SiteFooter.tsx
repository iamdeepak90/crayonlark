import Link from "next/link";
import type { SiteConfig } from "@/lib/public";
import { Logo } from "./Logo";
import { SubscribeForm } from "./SubscribeForm";

const EXPLORE = [
  { href: "/books", label: "Books" },
  { href: "/themes", label: "Themes" },
  { href: "/free-printables", label: "Free printables" },
  { href: "/blog", label: "Blog" },
  { href: "/about", label: "About" },
];

const HELP = [
  { href: "/parents-and-teachers", label: "Parents & teachers" },
  { href: "/how-we-make-our-books", label: "How we make our books" },
  { href: "/faq", label: "FAQ" },
  { href: "/contact", label: "Contact" },
  { href: "/license", label: "Printable license" },
  { href: "/privacy", label: "Privacy policy" },
  { href: "/terms", label: "Terms" },
];

function Social({ href, label, children }: { href: string; label: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener me" aria-label={label} className="grid h-9 w-9 place-items-center rounded-full bg-white/10 transition hover:bg-white/20">
      {children}
    </a>
  );
}

/** Dark footer: brand, links, monthly free pages sign-up, AI and Associates disclosures. */
export function SiteFooter({ config }: { config: SiteConfig }) {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto bg-ink text-white">
      <div className="mx-auto max-w-6xl px-5 pt-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr_1fr_1.4fr]">
          <div>
            <Logo dark />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/65">
              Little books for big imaginations. Coloring and activity books for kids ages 2–10.
            </p>
            <div className="mt-6 flex gap-3">
              {config.pinterest_profile_url && (
                <Social href={config.pinterest_profile_url} label="Crayonlark on Pinterest">
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 2a10 10 0 0 0-3.6 19.3c-.1-.8-.2-2 0-2.9l1.2-5s-.3-.6-.3-1.5c0-1.4.8-2.4 1.8-2.4.8 0 1.2.6 1.2 1.4 0 .9-.5 2.1-.8 3.3-.2 1 .5 1.8 1.5 1.8 1.8 0 3.1-1.9 3.1-4.6 0-2.4-1.7-4.1-4.2-4.1-2.9 0-4.5 2.1-4.5 4.4 0 .9.3 1.8.8 2.3a.3.3 0 0 1 0 .3l-.3 1.2c0 .2-.2.3-.4.2-1.3-.6-2.1-2.5-2.1-4 0-3.3 2.4-6.3 6.9-6.3 3.6 0 6.4 2.6 6.4 6 0 3.6-2.2 6.5-5.4 6.5-1.1 0-2.1-.6-2.4-1.2l-.7 2.5c-.2.9-.9 2.1-1.3 2.8A10 10 0 1 0 12 2z" />
                  </svg>
                </Social>
              )}
              {config.instagram_url && (
                <Social href={config.instagram_url} label="Crayonlark on Instagram">
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <rect x="3" y="3" width="18" height="18" rx="5" />
                    <circle cx="12" cy="12" r="4" />
                    <circle cx="17.5" cy="6.5" r="1" fill="currentColor" />
                  </svg>
                </Social>
              )}
              {config.etsy_shop_url && (
                <Social href={config.etsy_shop_url} label="Crayonlark shop on Etsy">
                  <span className="font-display text-sm font-semibold">E</span>
                </Social>
              )}
            </div>
          </div>
          <FooterLinks title="Explore" links={EXPLORE} />
          <FooterLinks title="Help" links={HELP} />
          <div>
            <h2 className="font-sans text-sm font-semibold text-white">Free pages by email</h2>
            <p className="mt-4 text-sm leading-relaxed text-white/65">A free printable pack, then new pages and activity ideas now and then.</p>
            <div className="mt-4">
              <SubscribeForm variant="footer" />
            </div>
          </div>
        </div>
        <div className="mt-14 flex flex-col gap-2 border-t border-white/10 py-6 text-xs text-white/55 md:flex-row md:justify-between md:gap-8">
          <p>
            © {year} Crayonlark. Designed by Crayonlark. Artwork is made with the help of AI tools, then checked and edited by a person.
          </p>
          {config.amazon_associates_tag && <p className="shrink-0">As an Amazon Associate we earn from qualifying purchases.</p>}
        </div>
      </div>
    </footer>
  );
}

function FooterLinks({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <nav aria-label={title}>
      <h2 className="font-sans text-sm font-semibold text-white">{title}</h2>
      <ul className="mt-4 space-y-3 text-sm text-white/65">
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href} className="transition hover:text-white">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
