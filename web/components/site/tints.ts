/**
 * Tinted surfaces use the secondary colour only (sun). 60/30/10 rule, see CLAUDE.md:
 * cream/white base ~60 %, sun ~30 %, coral accent ~10 %. Variety comes from doodles and emoji.
 */
export const TINT = { bg: "bg-sun-50", solid: "bg-sun-100", text: "text-sun-600", ink: "text-ink" } as const;
