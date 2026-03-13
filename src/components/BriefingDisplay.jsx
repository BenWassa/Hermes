import { Clock } from 'lucide-react';
import { DevelopmentCard } from './DevelopmentCard';

export function BriefingDisplay({ briefing }) {
  if (!briefing) return null;

  return (
    <div className="pb-24 max-w-2xl mx-auto space-y-8">
      <header className="pt-6 pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">GlobalBrief</h1>
        <p className="text-sm font-medium text-slate-500 uppercase tracking-widest mt-1">
          Daily Intelligence Briefing
        </p>
        <div className="mt-4 inline-flex items-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-3 py-1.5 rounded-full text-sm font-medium">
          <Clock size={14} />
          {briefing.date}
        </div>
      </header>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Today in 60 Seconds
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {briefing.today_in_60_seconds.map((item, index) => (
            <div
              key={index}
              className="bg-white dark:bg-slate-900 p-3 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col gap-2 active:scale-95 transition-transform"
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="text-sm font-medium text-slate-800 dark:text-slate-200 leading-tight">
                {item.headline}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Major Developments
        </h2>
        <div className="space-y-3">
          {briefing.major_developments.map((development) => (
            <DevelopmentCard key={development.id} development={development} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Analyst Consensus & Disagreement
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <h3 className="text-xs font-bold uppercase text-emerald-600 dark:text-emerald-400 mb-3">
              Consensus
            </h3>
            <ul className="space-y-3">
              {briefing.analyst_consensus.consensus.map((item, index) => (
                <li key={index} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <h3 className="text-xs font-bold uppercase text-rose-600 dark:text-rose-400 mb-3">
              Points of Friction
            </h3>
            <ul className="space-y-3">
              {briefing.analyst_consensus.friction.map((item, index) => (
                <li key={index} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Strategic Context
        </h2>
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
          <div className="max-w-none">
            {briefing.strategic_context.map((paragraph, index) => (
              <p
                key={index}
                className="text-slate-700 dark:text-slate-300 leading-relaxed mb-4 last:mb-0 text-[15px]"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">Watchlist</h2>
        <div className="bg-amber-50 dark:bg-amber-950/30 p-5 rounded-xl border border-amber-100 dark:border-amber-900/50 border-l-4 border-l-amber-500">
          <p className="text-amber-900 dark:text-amber-200 font-medium leading-relaxed">
            {briefing.watchlist}
          </p>
        </div>
      </section>
    </div>
  );
}
