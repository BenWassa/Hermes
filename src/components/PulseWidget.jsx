import { ArrowDownRight, Activity } from 'lucide-react';

const getStatusGlow = (status) => {
  if (!status) return 'bg-slate-500 shadow-[0_0_5px_rgba(148,163,184,0.5)]';
  const s = status.toUpperCase();

  // Tier 5 — CRITICAL / ESCALATING
  if (s.includes('CRIT') || s.includes('ESCALAT')) return 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)] animate-pulse';
  // Tier 4 — SEVERE / HIGH
  if (s.includes('SEVER') || s.includes('HIGH')) return 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.8)] animate-pulse';
  // Tier 3 — ELEVATED / VOLATILE / MONITOR
  if (s.includes('ELEVAT') || s.includes('VOLATIL') || s.includes('MONITOR')) return 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]';
  // Tier 2 — GUARDED / MODERATE / WATCH
  if (s.includes('GUARD') || s.includes('MODER') || s.includes('WATCH')) return 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]';
  // Tier 1 — NOMINAL / STABLE / HOLD / STABILIZING
  if (s.includes('STABIL') || s.includes('HOLD') || s.includes('NOMINAL')) return 'bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]';
  return 'bg-slate-400';
};

export function PulseWidget({ title = 'Pulse', items, onItemClick }) {
  const safeItems = Array.isArray(items) ? items : [];
  const apexItem = safeItems[0];
  const secondaryItems = safeItems.slice(1);

  if (safeItems.length === 0) return null;

  const renderCard = (item, index, isApex) => (
    <button
      key={item.id || item.headline || index}
      onClick={() => onItemClick?.(item.domain, item.id)}
      className={`group relative flex flex-col justify-between overflow-hidden rounded-2xl border bg-white/5 text-left shadow-[0_8px_30px_rgb(0,0,0,0.12)] backdrop-blur-xl outline-none transition-all duration-300 hover:bg-white/10 active:scale-95 ${
        isApex
          ? 'border-cyan-500/30 p-5 hover:border-cyan-400/60 active:bg-cyan-900/20'
          : 'border-white/10 p-3 sm:p-5 hover:border-cyan-500/40 active:bg-slate-800/50'
      }`}
      type="button"
    >
      <div className="mb-3 flex w-full items-start justify-between">
        <div className="flex items-center gap-2">
          <span className={`drop-shadow-md ${isApex ? 'text-xl' : 'text-[15px]'}`}>{item.icon}</span>
          {isApex ? (
            <div className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.4)]">
              Apex Signal
            </div>
          ) : null}
        </div>

        {item.status ? (
          <div className="flex items-center gap-1.5 rounded-[3px] border border-white/5 bg-slate-950/50 px-1.5 py-0.5">
            <div className={`h-1.5 w-1.5 rounded-full ${getStatusGlow(item.status)}`}></div>
            <span className="font-mono text-[8px] uppercase tracking-widest text-slate-300">{item.status}</span>
          </div>
        ) : null}
      </div>

      <div className={`relative z-10 w-full ${isApex ? 'mb-4' : 'mb-3 flex-1'}`}>
        <h3
          className={`font-semibold leading-snug text-white transition-colors group-hover:text-cyan-50 ${
            isApex ? 'mb-2 text-[17px]' : 'text-[13px] line-clamp-2'
          }`}
        >
          {item.headline}
        </h3>

        {isApex && item.summary ? (
          <p className="pr-4 text-[13px] font-medium leading-relaxed text-slate-400">
            <span className="mr-1.5 font-mono text-[10px] text-cyan-500/50">///</span>
            {item.summary}
          </p>
        ) : null}
      </div>

      <div className={`mt-auto flex w-full items-end justify-between border-t border-white/10 ${isApex ? 'pt-3' : 'gap-2 pt-2.5'}`}>
        {isApex ? (
          <>
            <div className="min-w-0 pr-2">
              {item.target ? (
                <span className="truncate font-mono text-[9px] uppercase tracking-widest text-slate-400">{item.target}</span>
              ) : null}
            </div>
            {item.metric ? (
              <div
                className={`shrink-0 flex items-center gap-1 rounded border border-white/5 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${
                  item.metric.includes('+') || item.metric.includes('-') || item.metric.includes('CRIT')
                    ? 'border-cyan-500/20 bg-cyan-950/20 text-cyan-300'
                    : 'bg-white/5 text-slate-300'
                }`}
              >
                <Activity size={10} strokeWidth={2.5} />
                {item.metric}
              </div>
            ) : null}
          </>
        ) : (
          <div className="flex w-full justify-end">
            {item.metric ? (
              <div
                className={`shrink-0 flex items-center gap-1 rounded border border-white/5 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${
                  item.metric.includes('+') || item.metric.includes('-') || item.metric.includes('CRIT')
                    ? 'border-cyan-500/20 bg-cyan-950/20 text-cyan-300'
                    : 'bg-white/5 text-slate-300'
                }`}
              >
                <Activity size={10} strokeWidth={2.5} />
                {item.metric}
              </div>
            ) : item.target ? (
              <span className="truncate font-mono text-[9px] uppercase tracking-widest text-slate-400">{item.target}</span>
            ) : null}
          </div>
        )}
      </div>

      <div className="absolute bottom-3 right-3 -translate-x-2 text-cyan-400 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100 group-active:scale-110 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">
        <ArrowDownRight size={14} strokeWidth={3} />
      </div>
    </button>
  );

  return (
    <section>
      <div className="mb-4 flex items-center justify-between border-l-2 border-cyan-500/40 pl-3">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] animate-pulse"></div>
          <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">{title}</h2>
        </div>
        <div className="hidden text-[9px] font-mono uppercase tracking-widest text-cyan-500/50 sm:block">
          Net-Assessment // {safeItems.length} Vectors
        </div>
      </div>

      <div className="space-y-3">
        {apexItem ? renderCard(apexItem, 0, true) : null}
        {secondaryItems.length ? (
          <div className="grid grid-cols-2 gap-3 auto-rows-fr">
            {secondaryItems.map((item, index) => renderCard(item, index + 1, false))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
