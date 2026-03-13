import { ArrowUpRight, FolderArchive } from 'lucide-react';

export function ArchiveView({ briefings, onOpenBriefing }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-blue-950/40 border border-blue-500/20 text-blue-300 shadow-[0_0_20px_rgba(96,165,250,0.12)] backdrop-blur-md mb-4">
          <FolderArchive size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Intelligence Archive
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em]">
          Historical Database Records: {briefings.length}
        </p>
      </header>

      {briefings.length === 0 ? (
        <div className="text-[13px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl">
          STATUS: No historical records located in local storage.
        </div>
      ) : (
        <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
          {briefings.map((briefing) => (
            <button
              key={briefing.id}
              onClick={() => onOpenBriefing(briefing.id)}
              className="w-full flex items-center justify-between py-4 border-b border-white/10 last:border-b-0 hover:bg-white/5 transition-colors text-left group"
            >
              <div className="flex-1 pr-6">
                <div className="flex items-center gap-4 mb-1.5">
                  <span className="text-[12px] font-bold text-slate-100 uppercase tracking-[0.2em]">
                    {briefing.date}
                  </span>
                  <span className="text-[9px] text-slate-400 uppercase tracking-[0.22em] bg-white/5 border border-white/10 px-2 py-1 rounded-full">
                    ID: {briefing.id.slice(0, 8)}
                  </span>
                </div>

                <div className="text-[13px] text-slate-400 truncate flex items-center gap-2">
                  <span className="text-cyan-400 text-[10px]">///</span>
                  {briefing.today_in_60_seconds?.[0]?.headline}
                  <span className="text-slate-600">|</span>
                  {briefing.today_in_60_seconds?.[1]?.headline}
                </div>
              </div>
              <div className="text-slate-500 group-hover:text-cyan-300 transition-colors">
                <ArrowUpRight size={20} strokeWidth={1.5} />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
