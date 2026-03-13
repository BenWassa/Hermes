import { ArrowUpRight, DatabaseZap } from 'lucide-react';

export function SearchView({ query, results, onQueryChange, onOpenBriefing }) {
  const resultList = Array.isArray(results) ? results : [];

  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-purple-950/40 border border-purple-500/20 text-purple-300 shadow-[0_0_20px_rgba(168,85,247,0.12)] backdrop-blur-md mb-4">
          <DatabaseZap size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Database Query
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em] font-mono">
          Global Intelligence Network Search
        </p>
      </header>

      <div className="relative mb-8 group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan-400 text-sm font-bold font-mono select-none drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">
          &gt;_
        </div>
        <input
          type="text"
          placeholder="ENTER KEYWORD, TAG, OR THEME..."
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-full py-4 pl-10 pr-4 text-[13px] font-mono text-white focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/40 transition-colors placeholder:text-slate-500 uppercase backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]"
          spellCheck={false}
          autoComplete="off"
        />
      </div>

      {query && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-[0.24em] font-mono text-slate-400 mb-2 px-2">
            <span>Query Results</span>
            <span className="text-purple-400">[{resultList.length} MATCHES]</span>
          </div>

          {resultList.length === 0 ? (
            <div className="text-[11px] text-slate-400 py-6 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
              STATUS: 0 signals found matching "{query}".
            </div>
          ) : (
            <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
              {resultList.map((briefing) => (
                <button
                  key={briefing.id}
                  onClick={() => onOpenBriefing(briefing.id)}
                  className="w-full flex items-start justify-between py-4 border-b border-white/10 last:border-b-0 hover:bg-white/5 transition-colors text-left group"
                >
                  <div className="flex-1 pr-6 min-w-0">
                    <div className="flex items-center gap-4 mb-2">
                      <span className="text-[12px] font-bold font-mono text-slate-100 uppercase tracking-[0.2em]">
                        {briefing.date}
                      </span>
                      <span className="text-[9px] font-mono text-purple-300 uppercase tracking-[0.22em] bg-purple-950/40 border border-purple-500/20 px-2 py-1 rounded-sm shadow-[0_0_10px_rgba(168,85,247,0.1)]">
                        SYS_ID: {briefing.id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="text-[13px] text-slate-400 line-clamp-2 leading-relaxed font-medium">
                      <span className="text-cyan-400 text-[10px] font-mono mr-2 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">///</span>
                      {briefing.major_developments?.map((development) => development.headline).join(' · ')}
                    </div>
                  </div>

                  <div className="text-slate-500 group-hover:text-cyan-300 transition-colors mt-1">
                    <ArrowUpRight size={20} strokeWidth={1.5} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
