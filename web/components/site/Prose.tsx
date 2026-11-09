/** Readable long-form text styles (Tailwind arbitrary variants, so no typography plugin is needed). */
export const PROSE_CLASS =
  "max-w-prose break-words text-[17px] leading-relaxed text-ink/90 [&_a]:font-semibold [&_a]:text-coral-600 [&_a]:underline [&_a]:underline-offset-4 [&_blockquote]:border-l-4 [&_blockquote]:border-sun-400 [&_blockquote]:pl-4 [&_blockquote]:text-muted [&_h2]:mt-10 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-ink [&_h3]:mt-6 [&_h3]:text-lg [&_h3]:font-bold [&_h3]:text-ink [&_img]:my-6 [&_img]:h-auto [&_img]:max-w-full [&_img]:rounded-2xl [&_li]:mt-1.5 [&_ol]:mt-4 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:mt-4 [&_strong]:text-ink [&_table]:mt-6 [&_table]:w-full [&_table]:text-left [&_table]:text-base [&_td]:border-b [&_td]:border-line [&_td]:py-2 [&_td]:pr-4 [&_th]:border-b-2 [&_th]:border-line [&_th]:py-2 [&_th]:pr-4 [&_ul]:mt-4 [&_ul]:list-disc [&_ul]:pl-6 [&_li::marker]:text-coral-400";

/**
 * Renders HTML that the API has already sanitized (books: p, b, i, ul, ol, li, br; posts: a bit more).
 */
export function Prose({ html, className = "" }: { html: string; className?: string }) {
  return <div className={`${PROSE_CLASS} ${className}`} dangerouslySetInnerHTML={{ __html: html }} />;
}
