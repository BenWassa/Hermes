import { ChevronDown } from 'lucide-react';

export function ArchiveView({ briefings, onOpenBriefing }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Intelligence Archive</h1>
      {briefings.length === 0 ? (
        <p className="text-slate-500">No historical briefings available.</p>
      ) : (
        <div className="space-y-3">
          {briefings.map((briefing) => (
            <button
              key={briefing.id}
              onClick={() => onOpenBriefing(briefing.id)}
              className="w-full flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm active:scale-[0.98] transition-all text-left"
            >
              <div>
                <div className="font-semibold text-slate-900 dark:text-white">{briefing.date}</div>
                <div className="text-sm text-slate-500 truncate max-w-[250px] mt-1">
                  {briefing.today_in_60_seconds[0]?.headline} &bull;{' '}
                  {briefing.today_in_60_seconds[1]?.headline}
                </div>
              </div>
              <ChevronDown size={20} className="text-slate-400 -rotate-90" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
