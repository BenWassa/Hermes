import { ArrowUpRight, FolderArchive, Plus } from 'lucide-react';

export function ArchiveView({ briefings, onOpenBriefing, onAdd }) {
  return (
    <div className="pb-32 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300 relative min-h-[calc(100vh-8rem)]">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-blue-950/40 border border-blue-500/20 text-blue-300 shadow-[0_0_20px_rgba(96,165,250,0.12)] backdrop-blur-md mb-4">
          <FolderArchive size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Intelligence Archive
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em] font-mono">
          Historical Database Records: {briefings.length}
        </p>
      </header>

      {briefings.length === 0 ? (
        <div className="text-[11px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
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
              <div className="min-w-0 flex-1 pr-4">
                <div className="mb-1.5 flex min-w-0 flex-wrap items-center gap-2 sm:gap-4">
                  <span className="min-w-0 break-words text-[12px] font-bold font-mono text-slate-100 uppercase tracking-[0.2em]">
                    {briefing.date}
                  </span>
                  <span className="max-w-full truncate text-[9px] font-mono text-cyan-400 uppercase tracking-[0.22em] bg-cyan-950/40 border border-cyan-500/20 px-2 py-1 rounded-sm shadow-[0_0_10px_rgba(34,211,238,0.1)]">
                    ID: {briefing.id.slice(0, 8)}
                  </span>
                </div>

                <div className="min-w-0 flex items-center gap-2 text-[13px] text-slate-400">
                  <span className="shrink-0 text-[10px] font-mono text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">///</span>
                  <span className="min-w-0 truncate font-medium">
                    {[briefing.today_in_60_seconds?.[0]?.headline, briefing.today_in_60_seconds?.[1]?.headline]
                      .filter(Boolean)
                      .join(' | ') || 'No pulse preview available.'}
                  </span>
                </div>
              </div>
              <div className="ml-3 shrink-0 text-slate-500 group-hover:text-cyan-300 transition-colors">
                <ArrowUpRight size={20} strokeWidth={1.5} />
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Prominent Import Button */}
      <div
        className="fixed left-0 w-full z-40 pointer-events-none flex justify-center px-6"
        style={{ bottom: 'max(8.25rem, calc(env(safe-area-inset-bottom) + 6.75rem))' }}
      >
        <div className="w-full max-w-2xl flex justify-end">
          <button
            onClick={onAdd}
            className="pointer-events-auto flex items-center gap-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-5 py-3.5 rounded-full font-bold uppercase tracking-wider text-xs font-mono shadow-[0_12px_30px_rgba(0,0,0,0.35),_0_0_25px_rgba(34,211,238,0.35)] hover:shadow-[0_16px_36px_rgba(0,0,0,0.4),_0_0_35px_rgba(34,211,238,0.5)] transition-all transform hover:scale-105"
          >
            <Plus size={18} strokeWidth={2.5} />
            Import Briefing
          </button>
        </div>
      </div>
    </div>
  );
}
