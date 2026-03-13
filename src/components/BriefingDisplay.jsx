import { Clock } from 'lucide-react';
import { DevelopmentCard } from './DevelopmentCard';

export function BriefingDisplay({ briefing }) {
  if (!briefing) return null;
  const todayIn60 = Array.isArray(briefing.today_in_60_seconds) ? briefing.today_in_60_seconds : [];
  const developments = Array.isArray(briefing.major_developments) ? briefing.major_developments : [];
  const consensus = Array.isArray(briefing?.analyst_consensus?.consensus)
    ? briefing.analyst_consensus.consensus
    : [];
  const friction = Array.isArray(briefing?.analyst_consensus?.friction)
    ? briefing.analyst_consensus.friction
    : [];
  const strategicContext = Array.isArray(briefing.strategic_context) ? briefing.strategic_context : [];

  return (
    <div className="pb-24 max-w-2xl mx-auto">
      <header className="pt-8 pb-6 border-b-2 border-slate-900 dark:border-white mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white uppercase">
          GlobalBrief
        </h1>
        <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest mt-1">
          Daily Intelligence Briefing
        </p>
        <div className="mt-6 inline-flex items-center gap-2 text-slate-900 dark:text-white font-mono text-xs font-bold uppercase tracking-wider bg-slate-200/50 dark:bg-slate-800/50 px-3 py-1.5 rounded-sm">
          <Clock size={12} strokeWidth={2.5} />
          {briefing.date}
        </div>
      </header>

      <div className="space-y-12">
        <section>
          <h2 className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-4">
            Today in 60 Seconds
          </h2>
          <div className="grid grid-cols-2 gap-px bg-slate-200 dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-sm overflow-hidden">
            {todayIn60.map((item, index) => (
              <div
                key={index}
                className="bg-slate-50 dark:bg-[#0B0F19] p-5 flex flex-col gap-3 hover:bg-slate-100 dark:hover:bg-slate-900/80 transition-colors active:scale-[0.98]"
              >
                <span className="text-2xl grayscale opacity-80">{item.icon}</span>
                <span className="text-[13px] font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                  {item.headline}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2 border-b border-slate-200 dark:border-slate-800 pb-3">
            Major Developments
          </h2>
          <div className="flex flex-col">
            {developments.map((development) => (
              <DevelopmentCard key={development.id} development={development} />
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-4">
            Analyst Consensus & Disagreement
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6 border border-slate-200 dark:border-slate-800 p-6 rounded-sm bg-white/50 dark:bg-[#0B0F19]/50">
            <div>
              <h3 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="w-2 h-2 bg-slate-900 dark:bg-white inline-block"></span> Consensus
              </h3>
              <ul className="space-y-4">
                {consensus.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-800 dark:text-slate-300 leading-relaxed">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="md:border-l border-slate-200 dark:border-slate-800 md:pl-8">
              <h3 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 border border-slate-500 dark:border-slate-400 inline-block"></span> Points of
                Friction
              </h3>
              <ul className="space-y-4">
                {friction.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-4">
            Strategic Context
          </h2>
          <div className="pr-4 md:pr-8">
            {strategicContext.map((paragraph, index) => (
              <p
                key={index}
                className="text-slate-800 dark:text-slate-200 leading-loose mb-5 last:mb-0 text-[14.5px]"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-[11px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-4">
            Watchlist
          </h2>
          <div className="border-l-2 border-slate-900 dark:border-white pl-5 py-1">
            <p className="text-slate-900 dark:text-white font-medium leading-relaxed text-[15px]">
              {briefing.watchlist}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
