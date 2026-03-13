import { Plus, ArrowRight, Terminal } from 'lucide-react';
import { BriefingDisplay } from '../components/BriefingDisplay';

export function HomeView({ activeBriefing, latestBriefing, onGoAdd, onOpenBriefing }) {
  if (activeBriefing) {
    return <BriefingDisplay briefing={activeBriefing} />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] px-4 max-w-sm mx-auto text-center space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col items-center">
        <div className="text-slate-900 dark:text-white mb-6 border-b-2 border-slate-900 dark:border-white pb-4 w-16 flex justify-center">
          <Terminal size={32} strokeWidth={1.5} />
        </div>
        <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight uppercase mb-3">
          Awaiting Input
        </h2>
        <p className="text-[14px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
          Your intelligence panel is currently empty for today. Paste your generated JSON to populate the dashboard.
        </p>
      </div>

      <div className="w-full space-y-4">
        <button
          onClick={onGoAdd}
          className="w-full flex items-center justify-center gap-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold py-4 px-6 rounded-sm shadow-sm active:scale-[0.98] transition-all uppercase tracking-wider text-[13px] font-mono"
        >
          <Plus size={18} strokeWidth={2.5} />
          Add Today's Briefing
        </button>

        {latestBriefing && (
          <button
            onClick={() => onOpenBriefing(latestBriefing.id)}
            className="w-full flex items-center justify-center gap-2 bg-transparent border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold py-3.5 px-6 rounded-sm hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-[0.98] transition-all uppercase tracking-wider text-[11px] font-mono"
          >
            Load Previous: {latestBriefing.date}
            <ArrowRight size={14} strokeWidth={2} />
          </button>
        )}
      </div>
    </div>
  );
}
