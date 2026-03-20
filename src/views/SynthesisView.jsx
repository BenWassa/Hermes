import { Layers } from 'lucide-react';
import { ThreadCard } from '../components/ThreadCard';

function SynthesisCard({ synthesis, onOpenThread }) {
  const activeThreads = Array.isArray(synthesis.active_threads) ? synthesis.active_threads : [];
  const thematicArcs = Array.isArray(synthesis.thematic_arcs) ? synthesis.thematic_arcs : [];
  const deltaRisks = Array.isArray(synthesis.delta_risks) ? synthesis.delta_risks : [];
  const phaseShifts = Array.isArray(synthesis.phase_shifts) ? synthesis.phase_shifts : [];

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)] overflow-hidden mb-6">
      <div className="px-5 py-4 border-b border-white/8 flex items-start justify-between gap-4">
        <div>
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.26em] text-cyan-400/70 mb-1">Synthesis Overlay</div>
          <div className="text-[13px] font-bold text-slate-100 font-mono">{synthesis.id}</div>
          {synthesis.date_range && (
            <div className="text-[10px] font-mono text-slate-500 mt-0.5 uppercase tracking-[0.16em]">
              {synthesis.date_range.from} → {synthesis.date_range.to}
            </div>
          )}
        </div>
        {synthesis.dominant_system ? (
          <div className="text-right">
            <div className="text-[9px] font-mono uppercase tracking-[0.18em] text-amber-400/60 mb-0.5">Dominant System</div>
            <div className="text-[11px] text-amber-200/80 font-medium">{synthesis.dominant_system}</div>
          </div>
        ) : null}
      </div>

      {activeThreads.length > 0 ? (
        <div className="px-5 py-3">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 mb-1">Active Threads</div>
          {activeThreads.map((thread) => (
            <ThreadCard key={thread.story_id} thread={thread} onOpen={onOpenThread} />
          ))}
        </div>
      ) : null}

      {thematicArcs.length > 0 ? (
        <div className="px-5 py-3 border-t border-white/5">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">Thematic Arcs</div>
          <ul className="space-y-1.5">
            {thematicArcs.map((arc, i) => (
              <li key={i} className="text-[13px] text-slate-300 leading-relaxed flex gap-2">
                <span className="text-purple-500/60 font-mono text-[10px] mt-0.5 shrink-0">›</span>
                {typeof arc === 'string' ? arc : arc.description || arc.title || JSON.stringify(arc)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {deltaRisks.length > 0 ? (
        <div className="px-5 py-3 border-t border-white/5">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">Risk Deltas</div>
          <ul className="space-y-1.5">
            {deltaRisks.map((risk, i) => (
              <li key={i} className="text-[12px] font-mono text-slate-400 flex gap-2 items-start">
                <span className="text-rose-500/60 shrink-0">△</span>
                <span>{typeof risk === 'string' ? risk : `${risk.story_id || ''} — ${risk.description || ''}`}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {phaseShifts.length > 0 ? (
        <div className="px-5 py-3 border-t border-white/5">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 mb-2">Phase Shifts</div>
          <ul className="space-y-1.5">
            {phaseShifts.map((shift, i) => (
              <li key={i} className="text-[12px] font-mono text-slate-400 flex gap-2 items-start">
                <span className="text-cyan-500/60 shrink-0">⟶</span>
                <span>{typeof shift === 'string' ? shift : `${shift.story_id || ''}: ${shift.from || ''} → ${shift.to || ''}`}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {synthesis.meta_findings ? (
        <div className="px-5 py-3 border-t border-white/5">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 mb-1.5">Meta Findings</div>
          <p className="text-[13px] text-slate-300 leading-relaxed">{synthesis.meta_findings}</p>
        </div>
      ) : null}
    </div>
  );
}

export function SynthesisView({ syntheses, onOpenThread }) {
  const list = Array.isArray(syntheses) ? syntheses : [];

  return (
    <div className="pb-32 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-purple-950/40 border border-purple-500/20 text-purple-300 shadow-[0_0_20px_rgba(168,85,247,0.12)] backdrop-blur-md mb-4">
          <Layers size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Synthesis
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em] font-mono">
          Cross-Day Intelligence Overlays: {list.length}
        </p>
      </header>

      {list.length === 0 ? (
        <div className="text-[11px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
          STATUS: No synthesis overlays imported. Paste a synthesis JSON to begin.
        </div>
      ) : (
        list.map((synthesis) => (
          <SynthesisCard key={synthesis.id} synthesis={synthesis} onOpenThread={onOpenThread} />
        ))
      )}
    </div>
  );
}
