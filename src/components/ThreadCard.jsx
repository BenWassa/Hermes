import { ArrowUpRight } from 'lucide-react';

const PHASE_COLORS = {
  escalation:  'text-rose-300 border-rose-500/20 bg-rose-950/20',
  active:      'text-amber-300 border-amber-500/20 bg-amber-950/20',
  emerging:    'text-cyan-300 border-cyan-500/20 bg-cyan-950/20',
  peak:        'text-orange-300 border-orange-500/20 bg-orange-950/20',
  stabilising: 'text-sky-300 border-sky-500/20 bg-sky-950/20',
  resolution:  'text-emerald-300 border-emerald-500/20 bg-emerald-950/20',
  default:     'text-slate-300 border-slate-500/20 bg-slate-800/20',
};

function phaseColor(phase) {
  const key = (phase || '').toLowerCase();
  return PHASE_COLORS[key] || PHASE_COLORS.default;
}

export function ThreadCard({ thread, onOpen }) {
  const phase = thread.phase || thread.status || '';
  const color = phaseColor(phase);

  return (
    <button
      type="button"
      onClick={() => onOpen?.(thread.story_id)}
      className="w-full text-left group flex items-start justify-between gap-4 py-4 border-b border-white/8 last:border-b-0 hover:bg-white/3 transition-colors"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="text-[13px] font-semibold text-slate-100 leading-snug">{thread.title || thread.story_id}</span>
          {phase ? (
            <span className={`text-[8px] font-mono font-bold uppercase tracking-[0.2em] px-1.5 py-0.5 rounded border ${color}`}>
              {phase}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 uppercase tracking-[0.16em]">
          <span className="text-cyan-500/60 font-bold select-none">///</span>
          <span>{thread.story_id}</span>
          {thread.first_seen && thread.last_seen ? (
            <span className="text-slate-600">{thread.first_seen} → {thread.last_seen}</span>
          ) : null}
        </div>
        {thread.summary ? (
          <p className="mt-1.5 text-[12px] text-slate-400 leading-relaxed line-clamp-2">{thread.summary}</p>
        ) : null}
      </div>
      <div className="shrink-0 text-slate-600 group-hover:text-cyan-400 transition-colors mt-0.5">
        <ArrowUpRight size={16} strokeWidth={1.5} />
      </div>
    </button>
  );
}
