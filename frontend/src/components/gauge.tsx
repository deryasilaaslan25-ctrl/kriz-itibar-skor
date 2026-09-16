import React, { useId } from "react";

export function Daire({ skor, renk }: { skor: number; renk: string }) {
  const radius = 44;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (Math.max(0, Math.min(100, skor)) / 100) * circ;
  const uid = useId();
  const gradId = `daire-grad-${uid}`;
  const glowId = `daire-glow-${uid}`;

  return (
    <div className="relative flex-shrink-0" style={{ width: 108, height: 108 }}>
      <svg width="108" height="108" style={{ transform: "rotate(-90deg)" }}>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={renk} stopOpacity="0.55" />
            <stop offset="100%" stopColor={renk} stopOpacity="1" />
          </linearGradient>
          <filter id={glowId} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="54" cy="54" r={radius} fill="none" className="stroke-muted" strokeWidth="9" />
        <circle
          cx="54"
          cy="54"
          r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth="9"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          filter={`url(#${glowId})`}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold tracking-tight font-display" style={{ color: renk }}>
          {Math.round(skor)}
        </span>
        <span className="text-[10px] font-medium text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}
