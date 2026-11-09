import { PageHeader } from "./PageHeader";
import { PROSE_CLASS } from "./Prose";

/**
 * Simple text page (About, Privacy, Terms, License). `template` adds an invisible HTML comment so
 * the owner remembers to have legal pages reviewed; visitors never see it.
 */
export function TextPage({
  title,
  intro,
  eyebrow,
  template,
  children,
}: {
  title: string;
  intro?: string;
  eyebrow?: string;
  template?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-5 py-14 sm:py-20">
      {template && <div hidden dangerouslySetInnerHTML={{ __html: "<!-- Template — review before launch -->" }} />}
      <PageHeader title={title} intro={intro} eyebrow={eyebrow} />
      <div className={`mt-8 rounded-3xl bg-white p-6 ring-1 ring-line sm:p-10 ${PROSE_CLASS} max-w-none [&>*:first-child]:mt-0`}>{children}</div>
    </div>
  );
}
