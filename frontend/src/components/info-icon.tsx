import React, { useState } from "react";
import { TERIMLER } from "@/lib/data";
import { Info } from "lucide-react";

export function InfoIcon({ term }: { term: keyof typeof TERIMLER }) {
  const [acik, setAcik] = useState(false);
  const g = TERIMLER[term];
  
  if (!g) return null;
  
  return (
    <span className="relative inline-block align-middle ml-1.5">
      <button
        type="button"
        onClick={() => setAcik((a) => !a)}
        onBlur={() => setTimeout(() => setAcik(false), 200)}
        className="text-muted-foreground/70 hover:text-signal focus:outline-none focus:ring-2 focus:ring-signal focus:ring-offset-1 rounded-full transition-colors"
        aria-label={`${g.baslik} açıklaması`}
      >
        <Info className="w-4 h-4" />
      </button>
      {acik && (
        <div className="absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 text-left rounded-xl shadow-xl p-3.5 w-64 bg-sidebar text-slate-100 border border-sidebar-border animate-in fade-in slide-in-from-bottom-2">
          <p className="text-xs font-bold text-white mb-1.5 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-signal" />
            {g.baslik}
          </p>
          <p className="text-[11px] text-slate-300 leading-relaxed">{g.aciklama}</p>
          <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-sidebar border-b border-r border-sidebar-border rotate-45" />
        </div>
      )}
    </span>
  );
}
