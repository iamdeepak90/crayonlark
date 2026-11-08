"use client";

import { useEffect, useRef } from "react";

/** Time (ms) when the form appeared in the browser. The API treats very fast submits as bots. */
export function useStartedAt() {
  const startedAt = useRef(0);
  useEffect(() => {
    startedAt.current = Date.now();
  }, []);
  return startedAt;
}
