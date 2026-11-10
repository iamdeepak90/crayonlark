"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

/** shadcn/ui toaster (Sonner), using the admin's zinc tokens. Radius stays ≤ 8px. */
export function Toaster(props: ToasterProps) {
  return (
    <Sonner
      position="bottom-right"
      closeButton
      style={
        {
          "--normal-bg": "var(--card)",
          "--normal-text": "var(--card-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "8px",
        } as React.CSSProperties
      }
      toastOptions={{ classNames: { toast: "font-sans shadow-lg", description: "!text-muted-foreground" } }}
      {...props}
    />
  );
}
