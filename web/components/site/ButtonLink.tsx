import Link from "next/link";

const VARIANTS = {
  primary: "bg-coral-600 text-white shadow-soft hover:bg-ink",
  dark: "bg-ink text-white hover:bg-ink/85",
  outline: "bg-white text-ink ring-1 ring-line hover:ring-ink/25",
  sun: "bg-sun-400 text-ink hover:bg-sun-100",
};

type Variant = keyof typeof VARIANTS;

type Props = {
  href: string;
  children: React.ReactNode;
  variant?: Variant;
  size?: "md" | "sm";
  external?: boolean;
  rel?: string;
  className?: string;
};

export const buttonClass = (variant: Variant = "primary", size: "md" | "sm" = "md") =>
  `inline-flex items-center justify-center gap-1.5 rounded-full text-center font-semibold transition ${
    size === "sm" ? "px-5 py-2.5 text-sm" : "px-6 py-3"
  } ${VARIANTS[variant]}`;

/** A link that looks like a pill button. External links open in a new tab. */
export function ButtonLink({ href, children, variant = "primary", size = "md", external, rel, className = "" }: Props) {
  const cls = `${buttonClass(variant, size)} ${className}`;
  if (external) {
    return (
      <a href={href} target="_blank" rel={rel ?? "noopener"} className={cls}>
        {children}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {children}
    </Link>
  );
}
