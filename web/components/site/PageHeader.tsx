/** Title block at the top of a page: small coloured eyebrow, serif title, intro. */
export function PageHeader({
  title,
  intro,
  eyebrow,
  center = false,
}: {
  title: string;
  intro?: React.ReactNode;
  eyebrow?: string;
  center?: boolean;
}) {
  return (
    <div className={`max-w-3xl ${center ? "mx-auto text-center" : ""}`}>
      {eyebrow && <p className="text-sm font-semibold text-coral-600">{eyebrow}</p>}
      <h1 className={`${eyebrow ? "mt-2" : ""} font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl`}>{title}</h1>
      {intro && <p className="mt-4 text-lg leading-relaxed text-muted">{intro}</p>}
    </div>
  );
}

/** Heading row for a section, with an optional link or button on the right. */
export function SectionHeading({
  id,
  eyebrow,
  eyebrowClass = "text-coral-600",
  title,
  intro,
  action,
}: {
  id?: string;
  eyebrow?: string;
  eyebrowClass?: string;
  title: string;
  intro?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-6">
      <div className="max-w-xl">
        {eyebrow && <p className={`text-sm font-semibold ${eyebrowClass}`}>{eyebrow}</p>}
        <h2 id={id} className={`${eyebrow ? "mt-2" : ""} font-display text-3xl font-semibold tracking-tight sm:text-4xl`}>
          {title}
        </h2>
        {intro && <p className="mt-2 text-muted">{intro}</p>}
      </div>
      {action}
    </div>
  );
}
