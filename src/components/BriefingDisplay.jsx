import { useMemo, useState } from 'react';
import { Zap, Layers } from 'lucide-react';
import { DevelopmentCard } from './DevelopmentCard';

export function BriefingDisplay({ briefing }) {
  const [activeDomain, setActiveDomain] = useState('ALL');
  const todayIn60 = Array.isArray(briefing?.today_in_60_seconds) ? briefing.today_in_60_seconds : [];
  const developments = Array.isArray(briefing?.major_developments) ? briefing.major_developments : [];
  const consensus = Array.isArray(briefing?.analyst_consensus?.consensus)
    ? briefing.analyst_consensus.consensus
    : [];
  const friction = Array.isArray(briefing?.analyst_consensus?.friction) ? briefing.analyst_consensus.friction : [];
  const strategicContext = Array.isArray(briefing?.strategic_context) ? briefing.strategic_context : [];

  const meceDomains = useMemo(() => {
    const domains = developments.map((dev) => dev.domain || 'MACRO');
    const uniqueDomains = new Set(domains);
    return ['ALL', ...Array.from(uniqueDomains)];
  }, [developments]);

  const filteredDevelopments = useMemo(() => {
    if (activeDomain === 'ALL') return developments;
    return developments.filter((dev) => (dev.domain || 'MACRO') === activeDomain);
  }, [activeDomain, developments]);

  if (!briefing) return null;

  return (
    <div className="pb-32 max-w-2xl mx-auto px-4">
      <header className="pt-8 pb-6 flex flex-col items-center text-center">
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.4)] mb-2">
          GlobalBrief
        </h1>
        <div className="inline-flex items-center gap-2 bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 px-4 py-1.5 rounded-full text-[11px] font-bold tracking-widest uppercase shadow-[0_0_15px_rgba(34,211,238,0.15)] backdrop-blur-md">
          <Zap size={14} className="animate-pulse" />
          {briefing.date}
        </div>
      </header>

      <div className="space-y-8">
        <section>
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">60-Second Pulse</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {todayIn60.map((item, index) => (
              <div
                key={index}
                className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 flex flex-col gap-3 shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:bg-white/10 hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] transition-all duration-300 active:scale-95"
              >
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border border-white/5 flex items-center justify-center text-2xl shadow-inner">
                  {item.icon}
                </div>
                <span className="text-[14px] font-semibold text-white leading-snug">{item.headline}</span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Tactical Breakdown</h2>
          </div>

          <div className="flex overflow-x-auto hide-scrollbar gap-2 mb-5 pb-2 -mx-4 px-4 md:mx-0 md:px-0">
            {meceDomains.map((domain) => {
              const isActive = activeDomain === domain;
              return (
                <button
                  key={domain}
                  onClick={() => setActiveDomain(domain)}
                  className={`whitespace-nowrap px-4 py-2 rounded-full text-[10px] font-mono font-bold uppercase tracking-widest transition-all duration-300 backdrop-blur-md flex items-center gap-2 ${
                    isActive
                      ? 'bg-cyan-950/60 border border-cyan-400/50 text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.2)] scale-105'
                      : 'bg-white/5 border border-white/10 text-slate-400 hover:text-slate-200 hover:bg-white/10'
                  }`}
                >
                  {isActive && <Layers size={12} className="text-cyan-400" />}
                  {domain}
                </button>
              );
            })}
          </div>

          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl px-5 py-3 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
            <div className="flex flex-col animate-in fade-in slide-in-from-bottom-2 duration-500">
              {filteredDevelopments.length > 0 ? (
                filteredDevelopments.map((development) => (
                  <DevelopmentCard key={development.id} development={development} />
                ))
              ) : (
                <div className="text-center py-8 text-slate-500 font-mono text-[11px] uppercase tracking-widest bg-white/5 border border-white/10 rounded-2xl">
                  No active signals in this sector.
                </div>
              )}
            </div>
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Network Consensus</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-gradient-to-br from-cyan-950/30 to-slate-900/40 backdrop-blur-xl p-5 rounded-2xl border border-cyan-500/20 shadow-[0_0_20px_rgba(34,211,238,0.05)]">
              <h3 className="text-[11px] font-extrabold uppercase tracking-widest text-cyan-400 mb-4">Verified Patterns</h3>
              <ul className="space-y-3">
                {consensus.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-200 leading-relaxed flex gap-2">
                    <span className="text-cyan-500 font-bold">›</span> {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gradient-to-br from-amber-950/30 to-slate-900/40 backdrop-blur-xl p-5 rounded-2xl border border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.05)]">
              <h3 className="text-[11px] font-extrabold uppercase tracking-widest text-amber-500 mb-4">Friction Points</h3>
              <ul className="space-y-3">
                {friction.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-200 leading-relaxed flex gap-2">
                    <span className="text-amber-500 font-bold">›</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(165,243,252,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Strategic Context</h2>
          </div>
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
            {strategicContext.map((paragraph, index) => (
              <p key={index} className="text-slate-200 leading-loose mb-4 last:mb-0 text-[14.5px]">
                {paragraph}
              </p>
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Watchlist</h2>
          </div>
          <div className="bg-gradient-to-r from-amber-950/40 to-transparent backdrop-blur-xl border border-amber-500/20 rounded-2xl px-5 py-4">
            <p className="text-amber-100 font-medium leading-relaxed text-[15px]">{briefing.watchlist}</p>
          </div>
        </section>
      </div>
    </div>
  );
}
