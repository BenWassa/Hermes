import { ArrowUpRight, DatabaseZap } from 'lucide-react';

export function SearchView({ query, results, onQueryChange, onOpenBriefing }) {
  const resultList = Array.isArray(results) ? results : [];

  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="mb-8 border-b-2 border-slate-900 dark:border-white pb-4">
        <div className="flex items-center gap-3 mb-2">
          <DatabaseZap size={24} strokeWidth={2} className="text-slate-900 dark:text-white" />
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white uppercase tracking-tight">
            Database Query
          </h1>
        </div>
        <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest">
          Global Intelligence Network Search
        </p>
      </header>

      <div className="relative mb-8 group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-600 font-mono text-sm font-bold select-none">
          &gt;_
        </div>
        <input
          type="text"
          placeholder="ENTER KEYWORD, TAG, OR THEME..."
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="w-full bg-slate-200/50 dark:bg-[#05080f] border border-slate-300 dark:border-slate-700 rounded-sm py-4 pl-10 pr-4 text-[13px] font-mono text-slate-900 dark:text-white focus:outline-none focus:border-slate-900 dark:focus:border-slate-400 focus:ring-1 focus:ring-slate-900 dark:focus:ring-slate-400 transition-colors placeholder:text-slate-400 dark:placeholder:text-slate-600 uppercase"
          spellCheck={false}
          autoComplete="off"
        />
      </div>

      {query && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400 mb-2">
            <span>Query Results</span>
            <span>[{resultList.length} MATCHES]</span>
          </div>

          {resultList.length === 0 ? (
            <div className="text-[13px] font-mono text-slate-500 py-6 border-t border-slate-200 dark:border-slate-800">
              STATUS: 0 signals found matching "{query}".
            </div>
          ) : (
            <div className="border-t border-slate-900 dark:border-slate-500">
              {resultList.map((briefing) => (
                <button
                  key={briefing.id}
                  onClick={() => onOpenBriefing(briefing.id)}
                  className="w-full flex items-start justify-between py-4 border-b border-slate-200 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-800/30 transition-colors text-left group"
                >
                  <div className="flex-1 pr-6">
                    <div className="flex items-center gap-4 mb-2">
                      <span className="text-[12px] font-mono font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                        {briefing.date}
                      </span>
                      <span className="text-[9px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest bg-slate-200 dark:bg-slate-800 px-1.5 py-0.5 rounded-[2px]">
                        SYS_ID: {briefing.id.slice(0, 8)}
                      </span>
                    </div>
                    <div className="text-[13px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                      <span className="text-slate-400 font-mono text-[10px] mr-2">///</span>
                      {briefing.major_developments?.map((development) => development.headline).join(' · ')}
                    </div>
                  </div>

                  <div className="text-slate-300 dark:text-slate-600 group-hover:text-slate-900 dark:group-hover:text-white transition-colors mt-1">
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
