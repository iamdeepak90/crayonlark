import { cn } from "@/lib/utils";

/** shadcn/ui tabs look for link- or button-based filters (no client state needed). */
export const tabsListClass = "inline-flex h-9 w-fit items-center rounded-lg bg-secondary p-[3px] text-muted-foreground";

export function tabClass(active: boolean) {
  return cn(
    "inline-flex h-full items-center justify-center whitespace-nowrap rounded-md px-2.5 text-sm font-medium capitalize transition-colors",
    active ? "bg-background text-foreground shadow-xs dark:bg-white/10" : "hover:text-foreground",
  );
}
