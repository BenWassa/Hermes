import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';

const QUADRANTS = [
  { key: 'watch', title: 'Watch Zone', position: 'col-start-1 row-start-2', tone: 'border-slate-700/60 bg-slate-900/60' },
  { key: 'structural', title: 'Structural Drift', position: 'col-start-1 row-start-1', tone: 'border-blue-500/20 bg-blue-950/20' },
  { key: 'volatile', title: 'Volatile but Contained', position: 'col-start-2 row-start-2', tone: 'border-amber-500/20 bg-amber-950/20' },
  { key: 'critical', title: 'Critical Zone', position: 'col-start-2 row-start-1', tone: 'border-red-500/25 bg-red-950/20' }
];

function getQuadrant(probability, impact) {
  const highProbability = probability >= 0.5;
  const highImpact = impact >= 0.5;

  if (highImpact && highProbability) return 'critical';
  if (highImpact) return 'structural';
  if (highProbability) return 'volatile';
  return 'watch';
}

export function RiskMatrixWidget({ title, risks }) {
  const safeRisks = Array.isArray(risks) ? risks.slice(0, 6) : [];
  const [activeId, setActiveId] = useState(safeRisks[0]?.id ?? null);

  if (safeRisks.length === 0) return null;

  return (
    <div className="bg-gradient-to-br from-red-950/10 to-slate-950/40 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <div className="flex items-center gap-2 mb-5">
        <AlertTriangle size={16} className="text-amber-400" />
        <h3 className="text-[11px] font-bold uppercase tracking-[0.24em] text-amber-300">{title}</h3>
      </div>

      <div className="relative grid grid-cols-2 grid-rows-2 gap-3">
        {QUADRANTS.map((quadrant) => {
          const items = safeRisks.filter((risk) => getQuadrant(risk.probability ?? 0, risk.impact ?? 0) === quadrant.key);
          return (
            <div
              key={quadrant.key}
              className={`${quadrant.position} min-h-32 rounded-2xl border p-3 ${quadrant.tone}`}
            >
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-300 mb-3">{quadrant.title}</div>
              <div className="space-y-2">
                {items.length > 0 ? (
                  items.map((risk) => {
                    const isActive = activeId === risk.id;
                    return (
                      <button
                        key={risk.id}
                        type="button"
                        onClick={() => setActiveId(isActive ? null : risk.id)}
                        className={`w-full rounded-xl border px-3 py-2 text-left transition-colors ${
                          isActive
                            ? 'border-cyan-400/40 bg-cyan-400/10 text-white'
                            : 'border-white/10 bg-black/20 text-slate-300 hover:text-white hover:border-white/20'
                        }`}
                      >
                        <div className="text-[12px] font-semibold leading-snug">{risk.label}</div>
                        {isActive ? (
                          <div className="mt-2 text-[12px] leading-relaxed text-slate-300">{risk.details}</div>
                        ) : null}
                      </button>
                    );
                  })
                ) : (
                  <div className="text-[11px] text-slate-500 uppercase tracking-[0.18em]">No active flags</div>
                )}
              </div>
            </div>
          );
        })}

        <div className="pointer-events-none absolute inset-y-0 left-1/2 -translate-x-1/2 w-px bg-white/10" />
        <div className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 h-px bg-white/10" />
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
        <span>Lower Probability</span>
        <span>Higher Probability</span>
      </div>
      <div className="mt-1 flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.18em] text-slate-500">
        <span>Higher Impact</span>
        <span>Lower Impact</span>
      </div>
    </div>
  );
}
