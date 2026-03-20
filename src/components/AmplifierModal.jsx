import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, X, Zap } from 'lucide-react';

const THEMES = {
  cyan: { eyebrow: 'text-cyan-400/80', border: 'border-cyan-500/20', bgOpen: 'bg-cyan-950/10', icon: 'text-cyan-500/50' },
  amber: { eyebrow: 'text-amber-400/80', border: 'border-amber-500/20', bgOpen: 'bg-amber-950/10', icon: 'text-amber-500/50' },
  purple: { eyebrow: 'text-purple-400/80', border: 'border-purple-500/20', bgOpen: 'bg-purple-950/10', icon: 'text-purple-500/50' },
  emerald: { eyebrow: 'text-emerald-400/80', border: 'border-emerald-500/20', bgOpen: 'bg-emerald-950/10', icon: 'text-emerald-500/50' },
  slate: { eyebrow: 'text-slate-400/80', border: 'border-white/10', bgOpen: 'bg-white/5', icon: 'text-slate-500/50' }
};

const STORY_ID_TOKEN_LABELS = {
  ai: 'AI',
  apac: 'APAC',
  boe: 'BoE',
  boj: 'BoJ',
  cpi: 'CPI',
  ecb: 'ECB',
  eu: 'EU',
  fed: 'Fed',
  fx: 'FX',
  g7: 'G7',
  g20: 'G20',
  ipo: 'IPO',
  mna: 'M&A',
  nato: 'NATO',
  opec: 'OPEC',
  pmi: 'PMI',
  pce: 'PCE',
  us: 'US',
  uk: 'UK',
  usd: 'USD'
};

function formatStoryIdLabel(storyId) {
  if (!storyId || typeof storyId !== 'string') return '';

  return storyId
    .replace(/^story[-_]/i, '')
    .split(/[-_]+/)
    .filter(Boolean)
    .map((token) => {
      const normalized = token.toLowerCase();
      if (STORY_ID_TOKEN_LABELS[normalized]) return STORY_ID_TOKEN_LABELS[normalized];
      return normalized.charAt(0).toUpperCase() + normalized.slice(1);
    })
    .join(' ');
}

function Section({ title, eyebrow, defaultOpen = false, theme = 'slate', children }) {
  const [open, setOpen] = useState(defaultOpen);
  const t = THEMES[theme] || THEMES.slate;

  return (
    <div className={`rounded-2xl overflow-hidden transition-colors border ${open ? t.border : 'border-white/8'} bg-white/[0.02] backdrop-blur-sm`}>
      <button
        type="button"
        onClick={() => setOpen((s) => !s)}
        className={`w-full flex items-center justify-between gap-4 px-4 py-3.5 text-left transition-colors hover:bg-white/5 ${open ? t.bgOpen : ''}`}
      >
        <div className="min-w-0 flex-1">
          {eyebrow ? (
            <div className={`text-[9px] font-bold font-mono uppercase tracking-[0.24em] mb-0.5 truncate ${t.eyebrow}`}>
              {eyebrow}
            </div>
          ) : null}
          <h3 className="text-[12px] font-bold font-mono uppercase tracking-[0.18em] text-slate-200 leading-snug truncate">
            {title}
          </h3>
        </div>
        <span className={`shrink-0 transition-transform ${t.icon}`}>
          {open ? <ChevronUp size={16} strokeWidth={2.5} /> : <ChevronDown size={16} strokeWidth={2.5} />}
        </span>
      </button>

      {open ? (
        <div className={`px-4 pb-4 animate-in fade-in slide-in-from-top-1 duration-200 ${t.bgOpen}`}>
          <div className="pt-2 border-t border-white/5">
            {children}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Bullet({ color = 'cyan', children }) {
  const markerColors = {
    cyan: 'text-cyan-400/60',
    amber: 'text-amber-400/60',
    red: 'text-rose-400/60'
  };

  return (
    <div className="flex items-start gap-2.5 text-[13px] text-slate-300 leading-relaxed py-1.5">
      <span className={`${markerColors[color] || markerColors.cyan} font-mono font-bold text-[10px] mt-1.5 shrink-0 select-none`}>///</span>
      <span className="break-words whitespace-normal min-w-0 flex-1">{children}</span>
    </div>
  );
}

function ClassBadge({ label }) {
  if (!label) return null;

  const colours = {
    structural: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30 shadow-[0_0_8px_rgba(34,211,238,0.15)]',
    cyclical: 'bg-amber-500/15 text-amber-300 border-amber-500/30 shadow-[0_0_8px_rgba(245,158,11,0.15)]',
    tactical: 'bg-purple-500/15 text-purple-300 border-purple-500/30 shadow-[0_0_8px_rgba(168,85,247,0.15)]',
    signaling: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 shadow-[0_0_8px_rgba(16,185,129,0.15)]'
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-[4px] border text-[9px] font-mono font-bold uppercase tracking-[0.2em] max-w-full truncate ${colours[label] || 'bg-white/10 text-slate-300 border-white/20'}`}>
      {label}
    </span>
  );
}

function MagnitudeBadge({ label }) {
  if (!label) return null;

  const colours = {
    HIGH: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    MEDIUM: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    LOW: 'text-slate-300 bg-white/5 border-white/10'
  };

  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded-[3px] border text-[9px] font-mono font-bold uppercase tracking-[0.2em] shrink-0 ${colours[label] || 'text-slate-400'}`}>
      {label}
    </span>
  );
}

function ScenarioBlock({ label, colour, data }) {
  if (!data) return null;

  const pct = Math.round((parseFloat(data.probability) || 0) * 100);

  const styles = {
    base: { bar: 'bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.6)]', text: 'text-cyan-300', bg: 'bg-cyan-950/20 border-cyan-500/20' },
    escalation: { bar: 'bg-rose-400 shadow-[0_0_10px_rgba(251,113,133,0.6)]', text: 'text-rose-300', bg: 'bg-rose-950/20 border-rose-500/20' },
    de_escalation: { bar: 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.6)]', text: 'text-emerald-300', bg: 'bg-emerald-950/20 border-emerald-500/20' }
  }[colour] || { bar: 'bg-slate-400', text: 'text-slate-300', bg: 'bg-white/5 border-white/10' };

  return (
    <div className={`rounded-xl border p-3.5 space-y-3 ${styles.bg}`}>
      <div className="flex items-center justify-between gap-2">
        <span className={`text-[10px] font-bold font-mono uppercase tracking-[0.2em] truncate ${styles.text}`}>
          {label}
        </span>
        <span className={`text-[11px] font-mono font-bold shrink-0 ${styles.text}`}>{pct}%</span>
      </div>

      <div className="h-1.5 rounded-full bg-slate-900 overflow-hidden border border-white/5">
        <div className={`h-full rounded-full ${styles.bar}`} style={{ width: `${pct}%` }} />
      </div>

      {data.path ? (
        <p className="text-[13px] text-slate-200 leading-relaxed break-words whitespace-normal min-w-0">
          {data.path}
        </p>
      ) : null}

      {(data.trigger || data.invalidator) ? (
        <div className="space-y-1.5 pt-2 border-t border-white/5">
          {data.trigger ? (
            <div className="text-[11px] text-slate-400 leading-snug break-words flex gap-2">
              <span className="text-cyan-400/60 font-mono font-bold text-[9px] uppercase tracking-widest shrink-0 mt-0.5">Trigger</span>
              <span className="break-words whitespace-normal min-w-0 flex-1">{data.trigger}</span>
            </div>
          ) : null}

          {data.invalidator ? (
            <div className="text-[11px] text-slate-400 leading-snug break-words flex gap-2">
              <span className="text-slate-500 font-mono font-bold text-[9px] uppercase tracking-widest shrink-0 mt-0.5">Breaks if</span>
              <span className="break-words whitespace-normal min-w-0 flex-1">{data.invalidator}</span>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function AmplifierModal({ amplifier, open, onClose }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open || !amplifier) return null;

  const { delta_lens, driver_decomposition, system_map, scenarios, second_order, transmission_map, decision_layer } = amplifier;
  const hasScenarios = scenarios && (scenarios.base || scenarios.escalation || scenarios.de_escalation);

  return (
    <div className="fixed inset-0 z-[60] flex flex-col sm:p-6 sm:items-center sm:justify-center">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity" onClick={onClose} />

      <div className="relative z-10 flex flex-col h-full min-h-0 sm:h-auto sm:max-h-[85vh] max-w-2xl w-full mx-auto bg-slate-950/90 sm:rounded-2xl sm:border border-white/10 shadow-[0_0_50px_rgba(8,145,178,0.15)] overflow-hidden animate-in fade-in slide-in-from-bottom-4 sm:zoom-in-95 duration-200">
        <div className="flex items-center justify-between gap-4 px-5 pt-safe sm:pt-4 pb-4 shrink-0 bg-slate-900/50 border-b border-white/10 backdrop-blur-xl">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg border border-cyan-500/30 bg-cyan-950/40 text-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.2)] shrink-0">
              <Zap size={16} strokeWidth={2.5} />
            </div>
            <div className="min-w-0">
              <div className="text-[9px] font-mono font-bold uppercase tracking-[0.28em] text-cyan-400/70 mb-0.5 truncate">
                Intelligence Layer
              </div>
              <h2 className="text-[16px] font-extrabold uppercase tracking-widest stark-gradient-text truncate drop-shadow-[0_0_8px_rgba(34,211,238,0.4)]">
                Amplifier
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-all shrink-0"
          >
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-5 py-4 space-y-4 hide-scrollbar pb-safe">
          {decision_layer && (
            (Array.isArray(decision_layer.what_matters_now) && decision_layer.what_matters_now.length > 0) ||
            (Array.isArray(decision_layer.watch_next) && decision_layer.watch_next.length > 0)
          ) ? (
            <Section title="Decision Layer" eyebrow="Action Signal" theme="amber" defaultOpen>
              {Array.isArray(decision_layer.what_matters_now) && decision_layer.what_matters_now.length > 0 ? (
                <div className="mb-4 bg-amber-950/20 border border-amber-500/10 rounded-xl p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_rgba(245,158,11,0.8)] shrink-0" />
                    <div className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-amber-400 truncate">What matters now</div>
                  </div>
                  {decision_layer.what_matters_now.map((item, i) => <Bullet key={i} color="amber">{item}</Bullet>)}
                </div>
              ) : null}
              {Array.isArray(decision_layer.watch_next) && decision_layer.watch_next.length > 0 ? (
                <div className="bg-cyan-950/20 border border-cyan-500/10 rounded-xl p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)] shrink-0" />
                    <div className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-cyan-400 truncate">Watch next</div>
                  </div>
                  {decision_layer.watch_next.map((item, i) => <Bullet key={i} color="cyan">{item}</Bullet>)}
                </div>
              ) : null}
            </Section>
          ) : null}

          {delta_lens && (
            (Array.isArray(delta_lens.system_shifts) && delta_lens.system_shifts.length > 0) ||
            (Array.isArray(delta_lens.threshold_crossings) && delta_lens.threshold_crossings.length > 0) ||
            (Array.isArray(delta_lens.invalidations) && delta_lens.invalidations.length > 0)
          ) ? (
            <Section title="Delta Lens" eyebrow="System Change" theme="cyan" defaultOpen>
              <div className="space-y-4">
                {Array.isArray(delta_lens.system_shifts) && delta_lens.system_shifts.length > 0 ? (
                  <div>
                    <div className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-cyan-400/80 mb-1.5">System shifts</div>
                    {delta_lens.system_shifts.map((item, i) => <Bullet key={i} color="cyan">{item}</Bullet>)}
                  </div>
                ) : null}
                {Array.isArray(delta_lens.threshold_crossings) && delta_lens.threshold_crossings.length > 0 ? (
                  <div>
                    <div className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-amber-400/80 mb-1.5">Threshold crossings</div>
                    {delta_lens.threshold_crossings.map((item, i) => <Bullet key={i} color="amber">{item}</Bullet>)}
                  </div>
                ) : null}
                {Array.isArray(delta_lens.invalidations) && delta_lens.invalidations.length > 0 ? (
                  <div>
                    <div className="text-[9px] font-mono font-bold uppercase tracking-[0.2em] text-rose-400/80 mb-1.5">Invalidations</div>
                    {delta_lens.invalidations.map((item, i) => <Bullet key={i} color="red">{item}</Bullet>)}
                  </div>
                ) : null}
              </div>
            </Section>
          ) : null}

          {hasScenarios ? (
            <Section title="Scenarios" eyebrow="Forward Paths" theme="purple" defaultOpen>
              <div className="space-y-3 pt-1">
                <ScenarioBlock label="Base" colour="base" data={scenarios.base} />
                <ScenarioBlock label="Escalation" colour="escalation" data={scenarios.escalation} />
                <ScenarioBlock label="De-escalation" colour="de_escalation" data={scenarios.de_escalation} />
              </div>
            </Section>
          ) : null}

          {Array.isArray(driver_decomposition) && driver_decomposition.length > 0 ? (
            <Section title="Driver Decomposition" eyebrow="Causal Layer" theme="emerald">
              <div className="space-y-3 pt-1">
                {driver_decomposition.map((item, i) => (
                  <div key={i} className="space-y-2 bg-white/[0.03] border border-white/5 p-3 rounded-xl min-w-0">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      {item.story_id ? (
                        <span className="text-[10px] font-mono text-slate-400 break-all bg-black/20 px-1.5 py-0.5 rounded max-w-full">
                          {formatStoryIdLabel(item.story_id)}
                        </span>
                      ) : null}
                      {item.classification ? <ClassBadge label={item.classification} /> : null}
                    </div>
                    {item.driver ? (
                      <p className="text-[13px] text-slate-200 leading-snug break-words whitespace-normal min-w-0">
                        {item.driver}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {Array.isArray(second_order) && second_order.length > 0 ? (
            <Section title="Second-Order Effects" eyebrow="Downstream" theme="slate">
              <div className="space-y-3 pt-1">
                {second_order.map((item, i) => (
                  <div key={i} className="space-y-1.5 border-t border-white/5 pt-3 first:border-0 first:pt-0 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      {item.domain ? (
                        <span className="text-[9px] font-mono font-bold text-cyan-400 uppercase tracking-widest break-words whitespace-normal max-w-full">
                          {item.domain}
                        </span>
                      ) : null}
                      {item.timing ? (
                        <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest break-words whitespace-normal bg-white/5 px-1.5 py-0.5 rounded shrink-0">
                          {item.timing}
                        </span>
                      ) : null}
                    </div>
                    {item.effect ? (
                      <p className="text-[13px] text-slate-300 leading-relaxed break-words whitespace-normal min-w-0">
                        {item.effect}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {Array.isArray(transmission_map) && transmission_map.length > 0 ? (
            <Section title="Transmission Map" eyebrow="Market Propagation" theme="slate">
              <div className="space-y-3 pt-1">
                {transmission_map.map((item, i) => (
                  <div key={i} className="rounded-xl border border-white/8 bg-white/[0.03] p-3.5 space-y-2 min-w-0">
                    <div className="flex items-center gap-2 text-[11px] font-mono flex-wrap min-w-0">
                      {item.from ? (
                        <span className="text-slate-200 font-bold break-words whitespace-normal bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-[4px] max-w-full">
                          {item.from}
                        </span>
                      ) : null}
                      <span className="text-cyan-500/50 font-bold shrink-0">→</span>
                      {item.to ? (
                        <span className="text-cyan-300 font-bold break-words whitespace-normal bg-cyan-950/40 border border-cyan-500/20 px-2 py-0.5 rounded-[4px] shadow-[0_0_8px_rgba(34,211,238,0.1)] max-w-full">
                          {item.to}
                        </span>
                      ) : null}
                    </div>
                    {item.channel ? (
                      <p className="text-[12px] text-slate-400 break-words whitespace-normal leading-relaxed min-w-0">
                        {item.channel}
                      </p>
                    ) : null}
                    <div className="flex items-center gap-3 flex-wrap pt-1 min-w-0">
                      {item.timing ? (
                        <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest break-words whitespace-normal bg-black/20 px-1.5 py-0.5 rounded shrink-0">
                          {item.timing}
                        </span>
                      ) : null}
                      {item.magnitude ? <MagnitudeBadge label={item.magnitude} /> : null}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {Array.isArray(system_map) && system_map.length > 0 ? (
            <Section title="System Map" eyebrow="Causal Chains" theme="cyan">
              <div className="space-y-4 pt-1">
                {system_map.map((item, i) => (
                  <div key={i} className="space-y-3 border-t border-white/10 pt-4 first:border-0 first:pt-0 min-w-0">
                    {Array.isArray(item.chain) && item.chain.length > 0 ? (
                      <div className="flex items-center gap-2 flex-wrap min-w-0">
                        {item.chain.map((node, j) => (
                          <span key={j} className="inline-flex items-center gap-2 max-w-full min-w-0">
                            <span className="text-[11px] font-mono text-cyan-100 bg-cyan-950/30 border border-cyan-500/20 shadow-[0_0_8px_rgba(34,211,238,0.05)] rounded-md px-2 py-1 break-words whitespace-normal max-w-full">
                              {node}
                            </span>
                            {j < item.chain.length - 1 ? <span className="text-cyan-500/40 text-[10px] shrink-0 font-bold">→</span> : null}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {item.summary ? (
                      <p className="text-[12px] text-slate-400 leading-relaxed border-l-2 border-cyan-500/30 pl-3 ml-1 break-words whitespace-normal min-w-0">
                        {item.summary}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
