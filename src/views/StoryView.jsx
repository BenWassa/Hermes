import { ArrowLeft, ArrowUpRight } from 'lucide-react';

const CHANGE_TYPE_COLORS = {
  new:         'text-cyan-300 border-cyan-500/30 bg-cyan-950/30',
  escalating:  'text-rose-300 border-rose-500/30 bg-rose-950/30',
  stabilizing: 'text-emerald-300 border-emerald-500/30 bg-emerald-950/30',
  resolving:   'text-blue-300 border-blue-500/30 bg-blue-950/30',
  unchanged:   'text-slate-400 border-slate-500/20 bg-slate-800/20',
};

const STAGE_COLORS = {
  emerging:       'text-cyan-400',
  active:         'text-amber-400',
  peak:           'text-orange-400',
  'winding-down': 'text-blue-400',
  resolved:       'text-emerald-400',
};

function changeTypeColor(ct) {
  return CHANGE_TYPE_COLORS[(ct || '').toLowerCase()] || CHANGE_TYPE_COLORS.unchanged;
}

function stageColor(stage) {
  return STAGE_COLORS[(stage || '').toLowerCase()] || 'text-slate-400';
}

export function StoryView({ storyId, briefings, syntheses, onBack, onOpenBriefing }) {
  const appearances = [];

  (briefings || []).forEach((briefing) => {
    const devs = Array.isArray(briefing.major_developments) ? briefing.major_developments : [];
    devs.forEach((dev) => {
      if (dev.story_id === storyId) {
        appearances.push({ briefingId: briefing.id, briefingDate: briefing.date, dev });
      }
    });
  });

  appearances.sort((a, b) => new Date(b.briefingId) - new Date(a.briefingId));

  const latestDev = appearances[0]?.dev;
  const title = latestDev?.headline || storyId;

  // Find any synthesis threads that cover this story
  const synthThreads = [];
  (syntheses || []).forEach((synth) => {
    (synth.active_threads || []).forEach((t) => {
      if (t.story_id === storyId) synthThreads.push({ synth, thread: t });
    });
  });

  return (
    <div className="pb-32 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-[0.22em] text-slate-500 hover:text-cyan-400 transition-colors mb-6"
      >
        <ArrowLeft size={14} strokeWidth={2} />
        Archive
      </button>

      <header className="mb-6">
        <div className="text-[9px] font-mono uppercase tracking-[0.26em] text-cyan-400/60 mb-1.5">{storyId}</div>
        <h1 className="text-[22px] font-extrabold text-white leading-snug tracking-tight mb-2">{title}</h1>
        <div className="text-[10px] font-mono text-slate-500 uppercase tracking-[0.18em]">
          {appearances.length} briefing{appearances.length !== 1 ? 's' : ''} · first seen {appearances[appearances.length - 1]?.briefingId || '—'} · last seen {appearances[0]?.briefingId || '—'}
        </div>
      </header>

      {synthThreads.length > 0 ? (
        <div className="mb-6 bg-purple-950/20 border border-purple-500/20 rounded-2xl px-5 py-4 backdrop-blur-xl">
          <div className="text-[9px] font-mono font-bold uppercase tracking-[0.26em] text-purple-400/70 mb-2">Synthesis Coverage</div>
          {synthThreads.map(({ synth, thread }, i) => (
            <div key={i} className="text-[12px] text-slate-300 leading-relaxed mb-1 last:mb-0">
              <span className="text-purple-400/60 mr-1.5">›</span>
              <span className="font-mono text-purple-300/60 mr-1.5">{synth.id}:</span>
              phase <span className="text-amber-300">{thread.phase || thread.status || '—'}</span>
              {thread.summary ? ` — ${thread.summary}` : ''}
            </div>
          ))}
        </div>
      ) : null}

      {appearances.length === 0 ? (
        <div className="text-[11px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
          STATUS: No briefings found for story ID "{storyId}".
        </div>
      ) : (
        <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
          {appearances.map(({ briefingId, briefingDate, dev }) => (
            <div key={briefingId} className="py-4 border-b border-white/8 last:border-b-0">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <span className="text-[11px] font-mono font-bold text-slate-300 uppercase tracking-[0.18em]">{briefingDate}</span>
                    {dev.change_type ? (
                      <span className={`text-[8px] font-mono font-bold uppercase tracking-[0.2em] px-1.5 py-0.5 rounded border ${changeTypeColor(dev.change_type)}`}>
                        {dev.change_type}
                      </span>
                    ) : null}
                    {dev.story_stage ? (
                      <span className={`text-[8px] font-mono uppercase tracking-[0.18em] ${stageColor(dev.story_stage)}`}>
                        {dev.story_stage}
                      </span>
                    ) : null}
                  </div>
                  {dev.driver ? (
                    <p className="text-[11px] font-mono text-amber-300/60 mb-1.5 uppercase tracking-[0.12em] leading-relaxed">
                      <span className="text-amber-500/40 mr-1">Driver:</span>{dev.driver}
                    </p>
                  ) : null}
                  {dev.headline !== title ? (
                    <p className="text-[13px] text-slate-400 leading-snug">{dev.headline}</p>
                  ) : null}
                  {dev.tags?.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {dev.tags.map((tag) => (
                        <span key={tag} className="text-[9px] font-mono uppercase tracking-[0.16em] text-slate-500 bg-white/5 border border-white/10 px-1.5 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => onOpenBriefing(briefingId)}
                  className="shrink-0 text-slate-600 hover:text-cyan-400 transition-colors mt-0.5"
                  aria-label={`Open briefing for ${briefingDate}`}
                >
                  <ArrowUpRight size={16} strokeWidth={1.5} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
