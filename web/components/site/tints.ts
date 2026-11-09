/** Soft background tints from the mockup, picked stably from a string (slug) so cards vary. */
export const TINTS = [
  { bg: "bg-sun-50", solid: "bg-sun-400", text: "text-sun-600", ink: "text-ink" },
  { bg: "bg-sky-50", solid: "bg-sky-400", text: "text-sky-600", ink: "text-white" },
  { bg: "bg-leaf-50", solid: "bg-leaf-400", text: "text-leaf-600", ink: "text-white" },
  { bg: "bg-coral-50", solid: "bg-coral-400", text: "text-coral-600", ink: "text-white" },
] as const;

export function tintFor(key: string) {
  let h = 0;
  for (const ch of key) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return TINTS[h % TINTS.length];
}
