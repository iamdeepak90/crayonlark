"use client";

import Script from "next/script";
import { useRef } from "react";

type TurnstileApi = {
  render: (el: HTMLElement, opts: { sitekey: string; callback: (token: string) => void; "expired-callback": () => void }) => string;
};

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

/**
 * Cloudflare Turnstile spam check. Only rendered when a site key is set in Settings → Keys and connections.
 * Re-mount it (change its `key`) to get a fresh token after a failed submit.
 */
export function Turnstile({ siteKey, onToken }: { siteKey: string; onToken: (token: string) => void }) {
  const box = useRef<HTMLDivElement>(null);

  function render() {
    if (!window.turnstile || !box.current || box.current.childElementCount > 0) return;
    window.turnstile.render(box.current, { sitekey: siteKey, callback: onToken, "expired-callback": () => onToken("") });
  }

  return (
    <>
      <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onReady={render} />
      <div ref={box} />
    </>
  );
}
