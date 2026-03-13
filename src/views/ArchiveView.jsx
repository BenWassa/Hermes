import { ArrowUpRight, FolderArchive } from 'lucide-react';

export function ArchiveView({ briefings, onOpenBriefing }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="mb-8 border-b-2 border-slate-900 dark:border-white pb-4">
        <div className="flex items-center gap-3 mb-2">
          <FolderArchive size={24} strokeWidth={2} className="text-slate-900 dark:text-white" />
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white uppercase tracking-tight">
            Intelligence Archive
          </h1>
        </div>
        <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest">
          Historical Database Records: {briefings.length}
        </p>
      </header>

      {briefings.length === 0 ? (
        <div className="text-[13px] font-mono text-slate-500 py-8 border-t border-slate-200 dark:border-slate-800">
          STATUS: No historical records located in local storage.
        </div>
      ) : (
        <div className="border-t border-slate-900 dark:border-slate-500">
          {briefings.map((briefing) => (
            <button
              key={briefing.id}
              onClick={() => onOpenBriefing(briefing.id)}
              className="w-full flex items-center justify-between py-4 border-b border-slate-200 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-800/30 transition-colors text-left group"
            >
              <div className="flex-1 pr-6">
                <div className="flex items-center gap-4 mb-1.5">
                  <span className="text-[12px] font-mono font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    {briefing.date}
                  </span>
                  <span className="text-[9px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest bg-slate-200 dark:bg-slate-800 px-1.5 py-0.5 rounded-[2px]">
                    ID: {briefing.id.slice(0, 8)}
                  </span>
                </div>

                <div className="text-[13px] text-slate-600 dark:text-slate-400 truncate flex items-center gap-2">
                  <span className="text-slate-400 font-mono text-[10px]">///</span>
                  {briefing.today_in_60_seconds?.[0]?.headline}
                  <span className="text-slate-300 dark:text-slate-600">|</span>
                  {briefing.today_in_60_seconds?.[1]?.headline}
                </div>
              </div>
              <div className="text-slate-300 dark:text-slate-600 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">
                <ArrowUpRight size={20} strokeWidth={1.5} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
