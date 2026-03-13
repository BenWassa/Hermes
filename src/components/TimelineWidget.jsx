import { useState } from 'react';
import { ChevronDown, ChevronUp, Crosshair } from 'lucide-react';

export function TimelineWidget({ title, events }) {
  const safeEvents = Array.isArray(events) ? events.slice(0, 8) : [];
  const [expandedIndex, setExpandedIndex] = useState(safeEvents.length > 0 ? 0 : null);

  if (safeEvents.length === 0) return null;

  return (
    <div className="bg-gradient-to-br from-cyan-950/20 to-slate-950/50 backdrop-blur-xl border border-cyan-500/15 rounded-2xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <div className="flex items-center gap-2 mb-6">
        <Crosshair size={16} className="text-cyan-400" />
        <h3 className="text-[11px] font-bold uppercase tracking-[0.24em] text-cyan-400">{title}</h3>
      </div>

      <div className="relative ml-3 border-l border-cyan-500/20 space-y-5">
        {safeEvents.map((event, index) => {
          const isExpanded = expandedIndex === index;
          const isLatest = index === 0;

          return (
            <div key={`${event.date}-${event.headline}-${index}`} className="relative pl-6">
              <div
                className={`absolute -left-[7px] top-1 h-3.5 w-3.5 rounded-full border-2 bg-slate-950 ${
                  isLatest
                    ? 'border-cyan-400 shadow-[0_0_14px_rgba(34,211,238,0.75)]'
                    : 'border-slate-600'
                }`}
              />

              <button
                type="button"
                onClick={() => setExpandedIndex(isExpanded ? null : index)}
                className="w-full flex items-start justify-between gap-3 text-left group"
              >
                <div className="min-w-0">
                  <div className={`text-[10px] font-mono font-bold uppercase tracking-[0.22em] mb-1 ${isLatest ? 'text-cyan-400' : 'text-slate-500'}`}>
                    {event.date}
                  </div>
                  <div className={`text-[14px] font-semibold leading-snug transition-colors ${isExpanded ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>
                    {event.headline}
                  </div>
                </div>

                <div className="shrink-0 mt-1 text-slate-500 group-hover:text-cyan-400 transition-colors">
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
              </button>

              {isExpanded ? (
                <div className="mt-3 pr-4 text-[13px] leading-relaxed text-slate-400 animate-in fade-in slide-in-from-top-2 duration-300">
                  <span className="mr-2 font-mono text-cyan-500/50">///</span>
                  {event.details}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
