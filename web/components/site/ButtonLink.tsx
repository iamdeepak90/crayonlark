import Link from "next/link";

const VARIANTS = {
  primary: "bg-coral-dark text-white hover:bg-ink",
  sun: "bg-sun text-ink hover:bg-sun-soft",
  dark: "bg-ink text-white hover:bg-ink-soft",
  outline: "border-2 border-ink text-ink hover:bg-white",
};

type Props = {
  href: string;
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
  external?: boolean;
  rel?: string;
};

export const buttonClass = (variant: keyof typeof VARIANTS = "primary") =>
  `inline-flex min-h-12 items-center justify-center rounded-full px-6 py-3 text-center font-display text-lg font-semibold transition-colors ${VARIANTS[variant]}`;

/** A link that looks like a button. External links open in a new tab. */
export function ButtonLink({ href, children, variant = "primary", external, rel }: Props) {
  if (external) {
    return (
      <a href={href} target="_blank" rel={rel ?? "noopener"} className={buttonClass(variant)}>
        {children}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    );
  }
  return (
    <Link href={href} className={buttonClass(variant)}>
      {children}
    </Link>
  );
}
