import { useEffect, useState } from 'react';
import { AlertTriangle } from 'lucide-react';

const QUADRANTS = [
  { key: 'structural', label: 'STRUCTURAL DRIFT', classes: 'top-0 left-0 border-r border-b border-white/10 bg-blue-950/20' },
  { key: 'critical', label: 'CRITICAL', classes: 'top-0 right-0 border-b border-white/10 bg-red-950/20' },
  { key: 'watch', label: 'WATCH', classes: 'bottom-0 left-0 border-r border-white/10 bg-slate-900/60' },
  { key: 'volatile', label: 'VOLATILE', classes: 'bottom-0 right-0 bg-amber-950/20' }
];

function getDotStyle(probability, impact) {
  const isHighProb = probability >= 0.5;
  const isHighImpact = impact >= 0.5;

  if (isHighImpact && isHighProb) return 'bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.8)] animate-pulse';
  if (isHighImpact) return 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.6)]';
  if (isHighProb) return 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]';
  return 'bg-slate-400 shadow-[0_0_6px_rgba(148,163,184,0.4)]';
}

export function RiskMatrixWidget({ title, risks }) {
  const safeRisks = Array.isArray(risks) ? risks : [];
  const [activeId, setActiveId] = useState(safeRisks[0]?.id ?? null);

  useEffect(() => {
    setActiveId((currentId) => {
      if (safeRisks.some((risk) => risk.id === currentId)) return currentId;
      return safeRisks[0]?.id ?? null;
    });
  }, [safeRisks]);

  if (safeRisks.length === 0) return null;

  const activeRisk = safeRisks.find((risk) => risk.id === activeId) || safeRisks[0];

  return (
    <div className="bg-gradient-to-br from-slate-900/50 to-slate-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <div className="flex items-center gap-2 mb-6">
        <AlertTriangle size={16} className="text-amber-400" />
        <h3 className="text-[11px] font-bold uppercase tracking-[0.24em] text-amber-300">{title}</h3>
      </div>

      <div className="flex">
        <div
          className="mr-4 flex items-center justify-center text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-slate-500"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        >
          Impact &uarr;
        </div>

        <div className="flex-1">
          <div className="relative mb-4 w-full overflow-hidden rounded-lg border border-white/10 aspect-square">
            {QUADRANTS.map((quadrant) => (
              <div key={quadrant.key} className={`absolute flex h-1/2 w-1/2 items-start p-2 ${quadrant.classes}`}>
                <span className="text-[9px] font-bold tracking-[0.2em] text-slate-500/50">{quadrant.label}</span>
              </div>
            ))}

            {safeRisks.map((risk) => {
              const isActive = activeId === risk.id;
              const probability = Math.max(0, Math.min(1, risk.probability || 0));
              const impact = Math.max(0, Math.min(1, risk.impact || 0));

              return (
                <button
                  key={risk.id}
                  type="button"
                  onClick={() => setActiveId(risk.id)}
                  className="absolute -translate-x-1/2 translate-y-1/2 outline-none transition-transform duration-300"
                  style={{ left: `${probability * 100}%`, bottom: `${impact * 100}%` }}
                >
                  <div className="absolute inset-[-12px] rounded-full" />
                  <div
                    className={`rounded-full transition-all duration-300 ${getDotStyle(probability, impact)} ${
                      isActive ? 'h-5 w-5 border-2 border-white' : 'h-3 w-3 border border-white/20'
                    }`}
                  />
                </button>
              );
            })}
          </div>

          <div className="text-center text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-slate-500">
            Probability &rarr;
          </div>
        </div>
      </div>

      {activeRisk ? (
        <div className="mt-6 animate-in fade-in slide-in-from-bottom-2 border-t border-white/10 pt-5">
          <div className="mb-2 flex items-start justify-between gap-4">
            <h4 className="text-[13px] font-bold leading-snug text-white">{activeRisk.label}</h4>
            <div className="shrink-0 rounded border border-cyan-500/20 bg-cyan-950/40 px-2 py-0.5 text-[10px] font-mono font-bold text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.1)]">
              P: {activeRisk.probability} | I: {activeRisk.impact}
            </div>
          </div>
          <p className="text-[13px] leading-relaxed text-slate-400">
            <span className="mr-2 font-mono text-[10px] text-cyan-500/50">///</span>
            {activeRisk.details}
          </p>
        </div>
      ) : null}
    </div>
  );
}
