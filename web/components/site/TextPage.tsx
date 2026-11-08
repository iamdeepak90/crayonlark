import { PageHeader } from "./PageHeader";
import { PROSE_CLASS } from "./Prose";

/**
 * Simple text page (About, Privacy, Terms, License). `template` adds an invisible HTML comment so
 * the owner remembers to have legal pages reviewed; visitors never see it.
 */
export function TextPage({
  title,
  intro,
  template,
  children,
}: {
  title: string;
  intro?: string;
  template?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      {template && <div hidden dangerouslySetInnerHTML={{ __html: "<!-- Template — review before launch -->" }} />}
      <PageHeader title={title} intro={intro} />
      <div className={`mt-6 ${PROSE_CLASS}`}>{children}</div>
    </div>
  );
}
