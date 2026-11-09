/** Simple line-art doodles (our own shapes) used as illustrations and placeholders. */

const S = { fill: "none", stroke: "#1F2430", strokeWidth: 3, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };

export function HouseDoodle() {
  return (
    <svg viewBox="0 0 100 100" className="h-full w-full" aria-hidden="true">
      <circle cx="74" cy="22" r="10" {...S} />
      <path d="M14 60 L36 38 L58 60 Z" {...S} />
      <rect x="20" y="60" width="32" height="28" {...S} />
      <rect x="31" y="72" width="10" height="16" fill="#FFE1D9" stroke="#1F2430" strokeWidth="2.5" />
      <path d="M8 90 L92 90" {...S} />
    </svg>
  );
}

export function RocketDoodle() {
  return (
    <svg viewBox="0 0 100 100" className="h-full w-full" aria-hidden="true">
      <path d="M50 10 C66 26 68 50 60 70 L40 70 C32 50 34 26 50 10 Z" {...S} />
      <circle cx="50" cy="38" r="8" fill="#DCF0FC" stroke="#1F2430" strokeWidth="3" />
      <path d="M40 58 L28 76 L42 71 Z M60 58 L72 76 L58 71 Z" {...S} />
      <path d="M44 72 Q50 92 56 72" {...S} />
    </svg>
  );
}

export function FishDoodle() {
  return (
    <svg viewBox="0 0 100 120" className="h-full w-full" aria-hidden="true">
      <ellipse cx="50" cy="62" rx="32" ry="24" {...S} />
      <circle cx="68" cy="55" r="2.6" fill="#1F2430" />
      <path d="M18 62 Q6 48 10 36 Q20 46 24 54" {...S} />
      <path d="M60 72 Q66 76 72 72" {...S} strokeWidth={2.6} />
      <circle cx="78" cy="22" r="4" {...S} strokeWidth={2.6} />
      <circle cx="86" cy="34" r="2.6" {...S} strokeWidth={2.6} />
    </svg>
  );
}

export function DinoDoodle({ className = "w-16" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 48" className={className} aria-hidden="true">
      <path
        d="M6 36c0-12 8-16 18-16h10c5 0 7-5 9-9 1.5-3 4-4 6.5-4 4 0 6.5 3 6.5 6.5 0 3-2.2 5-5 5.5l-2 .5C49 34 42 38 34 38H10z"
        fill="#fff"
        stroke="#1F2430"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />
      <circle cx="51" cy="13" r="1.6" fill="#1F2430" />
      <path d="M16 38v6M26 38v6M36 38v6" stroke="#1F2430" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function CloudDoodle() {
  return (
    <svg viewBox="0 0 64 64" className="h-full w-full" aria-hidden="true">
      <circle cx="46" cy="16" r="7" fill="none" stroke="#1F2430" strokeWidth="2" />
      <path d="M12 34a7 7 0 0 1 7-7 9 9 0 0 1 17 2 6 6 0 0 1 0 12H17a6 6 0 0 1-5-7z" fill="none" stroke="#1F2430" strokeWidth="2" strokeLinejoin="round" />
      <path d="M6 56h52M14 56c2-5 4-5 6 0M28 56c2-6 5-6 7 0M44 56c2-5 4-5 6 0" fill="none" stroke="#1F2430" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
