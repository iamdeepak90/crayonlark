/** Readable long-form text styles (Tailwind arbitrary variants, so no typography plugin is needed). */
export const PROSE_CLASS =
  "max-w-prose break-words text-lg leading-relaxed text-ink [&_a]:font-semibold [&_a]:text-coral-dark [&_a]:underline [&_blockquote]:border-l-4 [&_blockquote]:border-sun [&_blockquote]:pl-4 [&_h2]:mt-10 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-6 [&_h3]:text-xl [&_h3]:font-semibold [&_img]:my-6 [&_img]:h-auto [&_img]:max-w-full [&_img]:rounded-2xl [&_li]:mt-1 [&_ol]:mt-4 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:mt-4 [&_ul]:mt-4 [&_ul]:list-disc [&_ul]:pl-6";

/**
 * Renders HTML that the API has already sanitized (books: p, b, i, ul, ol, li, br; posts: a bit more).
 */
export function Prose({ html, className = "" }: { html: string; className?: string }) {
  return <div className={`${PROSE_CLASS} ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
