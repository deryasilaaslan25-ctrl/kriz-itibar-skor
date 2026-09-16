import React from "react";
import { Link, useLocation } from "wouter";
import { useAppContext } from "@/lib/app-context";
import { Shield, BarChart3, Newspaper, AlertTriangle, Settings, LogOut, Sparkles } from "lucide-react";

export function Navbar() {
  const { kullanici, aktifKrizSayisi, logout } = useAppContext();
  const [location] = useLocation();

  if (!kullanici) return null;

  const sekmeler = [
    { id: "/panel", ad: "Genel Bakış", ikon: <BarChart3 className="w-4 h-4 mr-2" /> },
    { id: "/icerikler", ad: "İçerik Akışı", ikon: <Newspaper className="w-4 h-4 mr-2" /> },
    { id: "/krizler", ad: "Kriz Merkezi", ikon: <AlertTriangle className="w-4 h-4 mr-2" /> },
    { id: "/pr-danismani", ad: "PR Danışmanı", ikon: <Sparkles className="w-4 h-4 mr-2" /> },
    { id: "/ayarlar", ad: "Ayarlar", ikon: <Settings className="w-4 h-4 mr-2" /> },
  ];

  return (
    <div className="sticky top-0 z-40 bg-sidebar/95 backdrop-blur-md border-b border-sidebar-border text-sidebar-foreground">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <div className="flex items-center gap-2.5 font-semibold font-display text-base tracking-wide">
          <div className="w-8 h-8 rounded-lg bg-signal/15 border border-signal/25 flex items-center justify-center">
            <Shield className="w-4 h-4 text-signal" />
          </div>
          <span className="hidden sm:inline text-slate-100">{kullanici.kurum}</span>
        </div>
        <div className="flex items-center gap-1 overflow-x-auto">
          {sekmeler.map((s) => {
            const aktif = location === s.id;
            return (
              <Link
                key={s.id}
                href={s.id}
                className={`relative flex items-center px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                  aktif
                    ? "bg-white/[0.06] text-white"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                }`}
              >
                {s.ikon}
                {s.ad}
                {s.id === "/krizler" && aktifKrizSayisi > 0 && (
                  <span className="absolute top-1.5 right-1.5 flex">
                    <span className="pulse-dot inline-flex w-1.5 h-1.5 rounded-full bg-red-500 text-red-500" />
                  </span>
                )}
                {aktif && (
                  <span className="absolute left-3 right-3 -bottom-px h-[2px] rounded-full bg-signal shadow-[0_0_8px_hsl(var(--signal-glow))]" />
                )}
              </Link>
            );
          })}
        </div>
        <button onClick={logout} className="flex items-center text-xs font-medium text-slate-400 hover:text-white transition-colors group">
          <LogOut className="w-4 h-4 mr-1.5 transition-transform group-hover:translate-x-0.5" />
          <span className="hidden sm:inline">Çıkış</span>
        </button>
      </div>
    </div>
  );
}
