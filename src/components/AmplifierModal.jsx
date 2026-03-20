import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';

function Section({ title, eyebrow, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-white/8 rounded-2xl overflow-hidden bg-white/3">
      <button
        type="button"
        onClick={() => setOpen((s) => !s)}
        className="w-full flex items-center justify-between gap-4 px-4 py-3.5 text-left"
      >
        <div>
          {eyebrow ? (
            <div className="text-[9px] font-bold font-mono uppercase tracking-[0.24em] text-cyan-400/70 mb-0.5">
              {eyebrow}
            </div>
          ) : null}
          <h3 className="text-[12px] font-bold font-mono uppercase tracking-[0.18em] text-slate-200">
            {title}
          </h3>
        </div>
        <span className="text-slate-500 shrink-0">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {open ? (
        <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-200">
          {children}
        </div>
      ) : null}
    </div>
  );
}

function Bullet({ children }) {
  return (
    <div className="flex items-start gap-2 text-[12px] text-slate-300 leading-snug py-1">
      <span className="text-cyan-400/60 font-mono text-[10px] mt-0.5 shrink-0">///</span>
      <span>{children}</span>
    </div>
  );
}

function ClassBadge({ label }) {
  const colours = {
    structural: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/25',
    cyclical: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
    tactical: 'bg-purple-500/15 text-purple-300 border-purple-500/25',
    signaling: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-lg border text-[9px] font-mono font-bold uppercase tracking-[0.18em] ${colours[label] || 'bg-white/10 text-slate-400 border-white/10'}`}>
      {label}
    </span>
  );
}

function MagnitudeBadge({ label }) {
  const colours = {
    HIGH: 'text-red-300',
    MEDIUM: 'text-amber-300',
    LOW: 'text-slate-400',
  };
  return (
    <span className={`text-[9px] font-mono font-bold uppercase tracking-[0.18em] ${colours[label] || 'text-slate-400'}`}>
      {label}
    </span>
  );
}

function ScenarioBlock({ label, colour, data }) {
  if (!data) return null;
  const pct = Math.round((data.probability || 0) * 100);

  const barColour = {
    base: 'bg-cyan-400',
    escalation: 'bg-red-400',
    de_escalation: 'bg-emerald-400',
  }[colour] || 'bg-slate-400';

  const textColour = {
    base: 'text-cyan-300',
    escalation: 'text-red-300',
    de_escalation: 'text-emerald-300',
  }[colour] || 'text-slate-300';

  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className={`text-[10px] font-bold font-mono uppercase tracking-[0.2em] ${textColour}`}>
          {label}
        </span>
        <span className={`text-[10px] font-mono font-bold ${textColour}`}>{pct}%</span>
      </div>

      <div className="h-1 rounded-full bg-white/8 overflow-hidden">
        <div className={`h-full rounded-full ${barColour}`} style={{ width: `${pct}%` }} />
      </div>

      <p className="text-[12px] text-slate-300 leading-snug">{data.path}</p>

      {data.trigger ? (
        <div className="text-[11px] text-slate-400 leading-snug">
          <span className="text-cyan-400/60 font-mono text-[9px] uppercase tracking-widest mr-1.5">Trigger</span>
          {data.trigger}
        </div>
      ) : null}

      {data.invalidator ? (
        <div className="text-[11px] text-slate-500 leading-snug">
          <span className="text-slate-600 font-mono text-[9px] uppercase tracking-widest mr-1.5">Breaks if</span>
          {data.invalidator}
        </div>
      ) : null}
    </div>
  );
}

export function AmplifierModal({ amplifier, open, onClose }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open || !amplifier) return null;

  const { delta_lens, driver_decomposition, system_map, scenarios, second_order, transmission_map, decision_layer } = amplifier;

  return (
    <div className="fixed inset-0 z-50 flex flex-col">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/85 backdrop-blur-md"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative z-10 flex flex-col h-full max-w-2xl w-full mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-safe pt-5 pb-4 shrink-0">
          <div>
            <div className="text-[9px] font-mono font-bold uppercase tracking-[0.28em] text-cyan-400/70 mb-0.5">
              Intelligence Layer
            </div>
            <h2 className="text-[15px] font-extrabold uppercase tracking-tight stark-gradient-text">
              Amplifier
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="w-9 h-9 flex items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={16} strokeWidth={2} />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-4 pb-10 space-y-3">

          {/* Decision Layer — always open */}
          {decision_layer ? (
            <Section title="Decision Layer" eyebrow="Action Signal" defaultOpen>
              {Array.isArray(decision_layer.what_matters_now) && decision_layer.what_matters_now.length > 0 ? (
                <div className="mb-3">
                  <div className="text-[9px] font-mono uppercase tracking-[0.2em] text-amber-400/70 mb-1.5">What matters now</div>
                  {decision_layer.what_matters_now.map((item, i) => <Bullet key={i}>{item}</Bullet>)}
                </div>
              ) : null}
              {Array.isArray(decision_layer.watch_next) && decision_layer.watch_next.length > 0 ? (
                <div>
                  <div className="text-[9px] font-mono uppercase tracking-[0.2em] text-cyan-400/70 mb-1.5">Watch next</div>
                  {decision_layer.watch_next.map((item, i) => <Bullet key={i}>{item}</Bullet>)}
                </div>
              ) : null}
            </Section>
          ) : null}

          {/* Delta Lens — open by default */}
          {delta_lens ? (
            <Section title="Delta Lens" eyebrow="System Change" defaultOpen>
              {Array.isArray(delta_lens.system_shifts) && delta_lens.system_shifts.length > 0 ? (
                <div className="mb-3">
                  <div className="text-[9px] font-mono uppercase tracking-[0.2em] text-cyan-400/70 mb-1.5">System shifts</div>
                  {delta_lens.system_shifts.map((item, i) => <Bullet key={i}>{item}</Bullet>)}
                </div>
              ) : null}
              {Array.isArray(delta_lens.threshold_crossings) && delta_lens.threshold_crossings.length > 0 ? (
                <div className="mb-3">
                  <div className="text-[9px] font-mono uppercase tracking-[0.2em] text-amber-400/70 mb-1.5">Threshold crossings</div>
                  {delta_lens.threshold_crossings.map((item, i) => <Bullet key={i}>{item}</Bullet>)}
                </div>
              ) : null}
              {Array.isArray(delta_lens.invalidations) && delta_lens.invalidations.length > 0 ? (
                <div>
                  <div className="text-[9px] font-mono uppercase tracking-[0.2em] text-red-400/70 mb-1.5">Invalidations</div>
                  {delta_lens.invalidations.map((item, i) => <Bullet key={i}>{item}</Bullet>)}
                </div>
              ) : null}
            </Section>
          ) : null}

          {/* Scenarios — open by default */}
          {scenarios ? (
            <Section title="Scenarios" eyebrow="Forward Paths" defaultOpen>
              <div className="space-y-2.5">
                <ScenarioBlock label="Base" colour="base" data={scenarios.base} />
                <ScenarioBlock label="Escalation" colour="escalation" data={scenarios.escalation} />
                <ScenarioBlock label="De-escalation" colour="de_escalation" data={scenarios.de_escalation} />
              </div>
            </Section>
          ) : null}

          {/* Driver Decomposition — collapsed */}
          {Array.isArray(driver_decomposition) && driver_decomposition.length > 0 ? (
            <Section title="Driver Decomposition" eyebrow="Causal Layer">
              <div className="space-y-3">
                {driver_decomposition.map((item, i) => (
                  <div key={i} className="space-y-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono text-slate-500">{item.story_id}</span>
                      {item.classification ? <ClassBadge label={item.classification} /> : null}
                    </div>
                    <p className="text-[12px] text-slate-300 leading-snug">{item.driver}</p>
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {/* Second-Order Effects — collapsed */}
          {Array.isArray(second_order) && second_order.length > 0 ? (
            <Section title="Second-Order Effects" eyebrow="Downstream">
              <div className="space-y-3">
                {second_order.map((item, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-mono font-bold text-slate-500 uppercase tracking-widest">{item.domain}</span>
                      <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">{item.timing}</span>
                    </div>
                    <p className="text-[12px] text-slate-300 leading-snug">{item.effect}</p>
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {/* Transmission Map — collapsed */}
          {Array.isArray(transmission_map) && transmission_map.length > 0 ? (
            <Section title="Transmission Map" eyebrow="Market Propagation">
              <div className="space-y-3">
                {transmission_map.map((item, i) => (
                  <div key={i} className="rounded-xl border border-white/8 bg-white/3 p-3 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-300 flex-wrap">
                      <span className="text-slate-200 font-bold">{item.from}</span>
                      <span className="text-slate-600">→</span>
                      <span className="text-cyan-300">{item.to}</span>
                    </div>
                    {item.channel ? (
                      <p className="text-[11px] text-slate-500">{item.channel}</p>
                    ) : null}
                    <div className="flex items-center gap-3">
                      <span className="text-[9px] font-mono text-slate-600 uppercase tracking-widest">{item.timing}</span>
                      {item.magnitude ? <MagnitudeBadge label={item.magnitude} /> : null}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          ) : null}

          {/* System Map — collapsed */}
          {Array.isArray(system_map) && system_map.length > 0 ? (
            <Section title="System Map" eyebrow="Causal Chains">
              <div className="space-y-3">
                {system_map.map((item, i) => (
                  <div key={i} className="space-y-2">
                    {Array.isArray(item.chain) ? (
                      <div className="flex items-start gap-1.5 flex-wrap">
                        {item.chain.map((node, j) => (
                          <span key={j} className="flex items-center gap-1.5">
                            <span className="text-[11px] text-slate-300 bg-white/5 border border-white/10 rounded-lg px-2 py-0.5">{node}</span>
                            {j < item.chain.length - 1 ? <span className="text-slate-600 text-[10px]">→</span> : null}
                          </span>
                        ))}
                      </div>
                    ) : null}
                    {item.summary ? (
                      <p className="text-[11px] text-slate-500 leading-snug">{item.summary}</p>
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
