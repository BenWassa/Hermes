import { useMemo } from 'react';
import { ArrowUpRight, DatabaseZap } from 'lucide-react';

const CHANGE_TYPE_COLORS = {
  escalating:  'text-rose-300 border-rose-500/30 bg-rose-950/30',
  new:         'text-cyan-300 border-cyan-500/30 bg-cyan-950/30',
  stabilizing: 'text-emerald-300 border-emerald-500/30 bg-emerald-950/30',
  resolving:   'text-blue-300 border-blue-500/30 bg-blue-950/30',
  unchanged:   'text-slate-400 border-slate-500/20 bg-slate-800/20',
};

function changeTypeColor(ct) {
  return CHANGE_TYPE_COLORS[(ct || '').toLowerCase()] || CHANGE_TYPE_COLORS.unchanged;
}

function matchesDev(dev, q) {
  const fields = [dev.headline, dev.story_id, dev.driver, dev.domain, dev.change_type, dev.story_stage, ...(dev.tags || [])];
  return fields.some((f) => typeof f === 'string' && f.toLowerCase().includes(q));
}

export function SearchView({ briefings, query, onQueryChange, onOpenBriefing, onOpenThread }) {
  const results = useMemo(() => {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];

    const hits = [];
    (briefings || []).forEach((briefing) => {
      const devs = Array.isArray(briefing.major_developments) ? briefing.major_developments : [];
      const matchedDevs = devs.filter((d) => matchesDev(d, q));

      const briefingLevelMatch =
        JSON.stringify({ id: briefing.id, date: briefing.date, today_in_60_seconds: briefing.today_in_60_seconds, watchlist: briefing.watchlist })
          .toLowerCase()
          .includes(q);

      if (matchedDevs.length > 0 || briefingLevelMatch) {
        hits.push({ briefing, matchedDevs: matchedDevs.length > 0 ? matchedDevs : null });
      }
    });

    return hits;
  }, [briefings, query]);

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
          placeholder="ENTER KEYWORD, STORY ID, TAG, OR DRIVER..."
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
            <span className="text-purple-400">[{results.length} MATCHES]</span>
          </div>

          {results.length === 0 ? (
            <div className="text-[11px] text-slate-400 py-6 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
              STATUS: 0 signals found matching "{query}".
            </div>
          ) : (
            <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
              {results.map(({ briefing, matchedDevs }) => (
                <div key={briefing.id} className="py-4 border-b border-white/10 last:border-b-0">
                  <button
                    onClick={() => onOpenBriefing(briefing.id)}
                    className="w-full text-left flex items-center justify-between gap-3 group mb-2"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-[12px] font-bold font-mono text-slate-100 uppercase tracking-[0.2em]">{briefing.date}</span>
                      <span className="text-[9px] font-mono text-purple-300 uppercase tracking-[0.22em] bg-purple-950/40 border border-purple-500/20 px-2 py-1 rounded-sm shadow-[0_0_10px_rgba(168,85,247,0.1)]">
                        {briefing.id.slice(0, 8)}
                      </span>
                    </div>
                    <ArrowUpRight size={16} strokeWidth={1.5} className="text-slate-600 group-hover:text-cyan-300 transition-colors shrink-0" />
                  </button>

                  {matchedDevs ? (
                    <ul className="space-y-2 mt-1">
                      {matchedDevs.map((dev, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-cyan-400/50 font-mono text-[10px] mt-0.5 select-none shrink-0">›</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="text-[12px] text-slate-300 leading-snug">{dev.headline}</span>
                              {dev.change_type ? (
                                <span className={`text-[8px] font-mono font-bold uppercase tracking-[0.2em] px-1.5 py-0.5 rounded border ${changeTypeColor(dev.change_type)}`}>
                                  {dev.change_type}
                                </span>
                              ) : null}
                            </div>
                            {dev.story_id ? (
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); onOpenThread?.(dev.story_id); }}
                                className="mt-1 text-[9px] font-mono text-cyan-400/60 hover:text-cyan-400 transition-colors uppercase tracking-[0.16em]"
                              >
                                {dev.story_id} →
                              </button>
                            ) : null}
                            {dev.driver ? (
                              <p className="text-[10px] font-mono text-amber-300/50 mt-0.5 uppercase tracking-[0.12em] line-clamp-1">{dev.driver}</p>
                            ) : null}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-[13px] text-slate-400 line-clamp-2 leading-relaxed font-medium flex gap-2 items-start">
                      <span className="text-cyan-400 text-[10px] font-mono drop-shadow-[0_0_5px_rgba(34,211,238,0.8)] shrink-0 mt-0.5">///</span>
                      <span>{briefing.major_developments?.map((d) => d.headline).join(' · ')}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
