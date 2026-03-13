import { ArrowDownRight } from 'lucide-react';

export function PulseWidget({ title = '60-Second Pulse', items, onItemClick }) {
  const safeItems = Array.isArray(items) ? items : [];

  if (safeItems.length === 0) return null;

  return (
    <section>
      <div className="mb-4 flex items-center gap-2 pl-1">
        <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
        <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">{title}</h2>
      </div>

      <div className="grid grid-cols-2 gap-3 auto-rows-fr">
        {safeItems.map((item, index) => {
          const isApex = index === 0;

          return (
            <button
              key={item.id || item.headline || index}
              onClick={() => onItemClick?.(item.domain)}
              className={`group relative overflow-hidden rounded-2xl border bg-white/5 text-left shadow-[0_8px_30px_rgb(0,0,0,0.12)] backdrop-blur-xl transition-all duration-300 hover:bg-white/10 active:scale-95 ${
                isApex
                  ? 'col-span-2 border-cyan-500/20 p-6 hover:border-cyan-400/40 hover:shadow-[0_0_24px_rgba(34,211,238,0.12)] active:bg-cyan-900/20'
                  : 'border-white/10 p-5 hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(34,211,238,0.1)] active:bg-slate-800/50'
              }`}
              type="button"
            >
              <div className="absolute bottom-3 right-3 text-cyan-400 opacity-30 transition-opacity duration-300 group-hover:opacity-100">
                <ArrowDownRight size={14} strokeWidth={2.5} />
              </div>

              <div className={`flex ${isApex ? 'items-center gap-4' : 'flex-col gap-3'}`}>
                <div
                  className={`shrink-0 rounded-full border border-white/5 bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center shadow-inner ${
                    isApex ? 'h-16 w-16 text-3xl' : 'h-12 w-12 text-2xl'
                  }`}
                >
                  {item.icon}
                </div>
                <div className="min-w-0 pr-4">
                  {isApex ? (
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.24em] text-cyan-400">
                      Apex Signal
                    </div>
                  ) : null}
                  <span className={`font-semibold leading-snug text-white ${isApex ? 'text-[18px]' : 'text-[14px]'}`}>
                    {item.headline}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
