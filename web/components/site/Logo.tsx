import Link from "next/link";

/** The lark mark: a little white bird on a sun-yellow circle. */
export function LarkMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="16" fill="#FFD45C" />
      <path
        d="M8 19c0-4.4 3.6-7 8-7 1-2.6 3-4 5.2-4 2 0 3.3 1.4 3.3 3.1 0 .6-.2 1.2-.5 1.7l2.5 1-2.9.9C23 19.9 20 23 15.5 23 11 23 8 21.6 8 19z"
        fill="#fff"
      />
      <circle cx="21.4" cy="11.2" r="1.1" fill="#1F2430" />
    </svg>
  );
}

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded-lg" aria-label="Crayonlark home">
      <LarkMark />
      <span className={`font-display text-xl font-semibold tracking-tight ${dark ? "text-white" : ""}`}>Crayonlark</span>
    </Link>
  );
}
