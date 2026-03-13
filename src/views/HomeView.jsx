import { AlertCircle, ArrowRight } from 'lucide-react';
import { BriefingDisplay } from '../components/BriefingDisplay';

export function HomeView({ activeBriefing, latestBriefing, onGoAdd, onOpenBriefing }) {
  if (activeBriefing) {
    return <BriefingDisplay briefing={activeBriefing} />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 max-w-md mx-auto text-center space-y-6">
      <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-2">
        <AlertCircle className="text-slate-400" size={32} />
      </div>
      <div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">No Briefing Loaded</h2>
        <p className="text-slate-500 dark:text-slate-400 mb-8">
          Your intelligence panel is currently empty for today. Paste your generated JSON to populate
          the dashboard.
        </p>
      </div>

      <button
        onClick={onGoAdd}
        className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-semibold py-4 px-6 rounded-xl shadow-md active:scale-[0.98] transition-all"
      >
        Add Today's Briefing
      </button>

      {latestBriefing && (
        <button
          onClick={() => onOpenBriefing(latestBriefing.id)}
          className="flex items-center justify-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors py-2"
        >
          View previous briefing
          <ArrowRight size={16} />
        </button>
      )}
    </div>
  );
}
